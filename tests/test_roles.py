from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_get_role_not_found():
    """测试查询不存在的角色"""
    response = client.get("/api/v1/roles/99999")
    assert response.status_code == 404

def test_update_role_not_found():
    """测试更新不存在的角色"""
    response = client.put("/api/v1/roles/99999", json={"name": "新名字"})
    assert response.status_code == 404

def test_delete_role_not_found():
    """测试删除不存在的角色"""
    response = client.delete("/api/v1/roles/99999")
    assert response.status_code == 404

def test_health_check():
    """测试健康检查接口"""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["code"] == 200