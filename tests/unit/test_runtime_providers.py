from stratbox.base.runtime import local_providers


def test_local_providers_have_independent_configuration(tmp_path):
    left = tmp_path / "left"
    right = tmp_path / "right"
    one = local_providers(root=str(left))
    two = local_providers(root=str(right))
    one.filestore.write_bytes("source.bin", b"one")
    two.filestore.write_bytes("source.bin", b"two")
    assert one.filestore.read_bytes("source.bin") == b"one"
    assert two.filestore.read_bytes("source.bin") == b"two"
    assert one.http is not two.http
