import copy
import json
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas
from app.models.domain import AppError
from app.repositories.store import Store
from app.services.documents import DocumentService
from app.services.sessions import SessionService
from app.services.tools import ToolService

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def system(tmp_path):
    store = Store(tmp_path/'test.db'); store.init()
    settings = SimpleNamespace(upload_dir=tmp_path/'uploads', max_upload_bytes=10*1024*1024)
    return store, DocumentService(store, settings), SessionService(store), ToolService(store)


def import_overview(documents):
    file = ROOT/'demo_documents/物件概要_demo.pdf'
    uploaded = documents.upload(file.name, file.read_bytes())
    return documents.parse(uploaded['id'])


def test_real_sdk_confirm_publish_pin_versions(system):
    store, documents, sessions, tools = system
    record = import_overview(documents)
    assert record['status'] == 'parsed'
    assert record['sdk_version'] == '1.8.0'
    assert record['normalized']['property']['price'] == 76900000
    assert record['normalized']['property']['land_area'] == 139.85
    assert 'walking_minutes' not in record['normalized']['property']
    with pytest.raises(AppError, match='確認済み'):
        documents.publish([record['id']])
    raw_before = json.dumps(record['raw'], ensure_ascii=False, sort_keys=True)
    documents.confirm(record['id'], copy.deepcopy(record['normalized']), 'TEST: generated official facts verified by assertion', usage='customer')
    v1 = documents.publish([record['id']])
    s1 = sessions.start('text', 'No.15')
    assert s1['version'] == v1['version']
    # Scenario B: change actual PDF bytes, re-run the actual SDK, then confirm.
    # This price is a synthetic isolated version-test value, not a market update.
    buffer = BytesIO(); pdf = canvas.Canvas(buffer)
    for i, line in enumerate(['property_name: Version test property', 'lot: No.15', 'price: 77000000', 'valid_until: 2026-10-15', 'effective_date: 2026-10-02']):
        pdf.drawString(50, 750-i*25, line)
    pdf.save()
    update = documents.parse(documents.upload('version_update_TEST.pdf', buffer.getvalue())['id'])
    assert update['sha256'] != record['sha256']
    assert update['normalized']['property']['price'] == 77000000
    documents.confirm(update['id'], copy.deepcopy(update['normalized']), 'TEST only: SDK-read changed PDF, synthetic price', usage='customer')
    v2 = documents.publish([update['id']])
    s2 = sessions.start('text', 'No.15')
    assert s2['version'] == v2['version']
    assert tools.execute(s1, 'get_property_overview', {})['property']['price'] == 76900000
    assert tools.execute(s2, 'get_property_overview', {})['property']['price'] == 77000000
    assert json.dumps(store.get('documents', record['id'])['raw'], ensure_ascii=False, sort_keys=True) == raw_before
    assert store.version(v1['version'])['document_ids'] == [record['id']]
    with pytest.raises(AppError):
        documents.publish([record['id'], update['id']])


def test_excel_rates_from_real_sdk_and_sources(system):
    _, documents, _, _ = system
    file = ROOT/'demo_documents/住宅ローン_demo.xlsx'
    record = documents.parse(documents.upload(file.name, file.read_bytes())['id'])
    rates = record['normalized']['rates']
    assert [r['rate'] for r in rates] == [1.195, 3.83]
    assert rates[1]['rate_over_90_percent'] == 3.94
    assert rates[0]['effective_date'] == '2026-10-01'
    assert rates[0]['reference']['location'] == 'Rates!2'
    assert record['normalized']['knowledge'] == []
    assert record['raw']['sheets'][0]['cells']
    documents.confirm(record['id'], copy.deepcopy(record['normalized']), 'TEST rate dates and conditions', usage='customer')


def test_wraps_and_all_equipment_are_retained(system):
    _, documents, _, _ = system
    file = ROOT/'demo_documents/設備仕様_demo.pdf'
    record = documents.parse(documents.upload(file.name,file.read_bytes())['id'])
    equipment = record['normalized']['property']['equipment']
    assert len(equipment) == 15
    assert any('読み替えをしていない' in e for e in equipment)
    assert record['normalized']['property']['source_url'].endswith('06top.html')


def test_file_validation_and_session_security(system):
    _, documents, sessions, _ = system
    for filename, data in [('x.exe',b'x'), ('x.pdf',b'fake'), ('x.xlsx',b'fake')]:
        with pytest.raises(AppError):
            documents.upload(filename, data)
    with pytest.raises(AppError):
        sessions.start('text', 'No.15')
    r = import_overview(documents)
    documents.confirm(r['id'], copy.deepcopy(r['normalized']), 'TEST', usage='customer')
    documents.publish([r['id']]); session = sessions.start('text', 'No.15')
    with pytest.raises(AppError):
        sessions.authorized(session['id'], 'wrong')
    sessions.end(session)
    with pytest.raises(AppError):
        sessions.authorized(session['id'], session['token'])
