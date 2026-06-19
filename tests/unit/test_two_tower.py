import pytest
import torch

from libs.ml.models import ItemTower, UserTower


@pytest.mark.parametrize("TowerClass", [UserTower, ItemTower])
class TestTowerShape:
    def test_output_shape(self, TowerClass):
        model = TowerClass(input_dim=16)
        model.eval()
        x = torch.randn(8, 16)
        with torch.no_grad():
            out = model(x)
        assert out.shape == (8, 32)

    def test_output_l2_normalized(self, TowerClass):
        model = TowerClass(input_dim=16)
        model.eval()
        x = torch.randn(8, 16)
        with torch.no_grad():
            out = model(x)
        norms = out.norm(dim=-1)
        assert torch.allclose(norms, torch.ones(8), atol=1e-5)

    def test_dot_product_in_range(self, TowerClass):
        model = TowerClass(input_dim=16)
        model.eval()
        with torch.no_grad():
            a = model(torch.randn(4, 16))
            b = model(torch.randn(4, 16))
        scores = (a * b).sum(dim=-1)
        assert scores.min().item() >= -1.0 - 1e-5
        assert scores.max().item() <= 1.0 + 1e-5

    def test_serialization_roundtrip(self, TowerClass, tmp_path):
        model = TowerClass(input_dim=16)
        model.eval()
        x = torch.randn(4, 16)
        with torch.no_grad():
            original_out = model(x)

        path = tmp_path / "tower.pt"
        torch.save(model, path)
        loaded = torch.load(path, weights_only=False)
        loaded.eval()
        with torch.no_grad():
            loaded_out = loaded(x)

        assert torch.allclose(original_out, loaded_out, atol=1e-6)


def test_user_and_item_tower_dot_product_in_range():
    user = UserTower(input_dim=10)
    item = ItemTower(input_dim=20)
    user.eval()
    item.eval()
    with torch.no_grad():
        u_emb = user(torch.randn(5, 10))
        i_emb = item(torch.randn(5, 20))
    scores = (u_emb * i_emb).sum(dim=-1)
    assert scores.min().item() >= -1.0 - 1e-5
    assert scores.max().item() <= 1.0 + 1e-5
