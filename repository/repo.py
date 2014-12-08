from tuf.repository_tool import *
import datetime

generate_and_write_rsa_keypair("/home/pankhuri/projects/repository/keystore/root_key", bits=2048, password="p")
generate_and_write_rsa_keypair("/home/pankhuri/projects/repository/keystore/root_key2")
public_root_key = import_rsa_publickey_from_file("/home/pankhuri/projects/repository/keystore/root_key.pub")
private_root_key = import_rsa_privatekey_from_file("/home/pankhuri/projects/repository/keystore/root_key")
generate_and_write_ed25519_keypair('/home/pankhuri/projects/repository/keystore//ed25519_key')
public_ed25519_key = import_ed25519_publickey_from_file('/home/pankhuri/projects/repository/keystore/ed25519_key.pub')

repository = create_new_repository("/home/pankhuri/projects/repository/repo/")
repository.root.add_verification_key(public_root_key)

public_root_key2 = import_rsa_publickey_from_file("/home/pankhuri/projects/repository/keystore/root_key2.pub")
repository.root.add_verification_key(public_root_key2)

repository.root.threshold = 2
private_root_key2 = import_rsa_privatekey_from_file("/home/pankhuri/projects/repository/keystore/root_key2", password="p")
repository.root.load_signing_key(private_root_key)
repository.root.load_signing_key(private_root_key2)
try:
  repository.write()
except tuf.UnsignedMetadataError, e:
  print e

generate_and_write_rsa_keypair("/home/pankhuri/projects/repository/keystore/targets_key", password="p")
generate_and_write_rsa_keypair("/home/pankhuri/projects/repository/keystore/snapshot_key", password="p")
generate_and_write_rsa_keypair("/home/pankhuri/projects/repository/keystore/timestamp_key", password="p")

repository.targets.add_verification_key(import_rsa_publickey_from_file("/home/pankhuri/projects/repository/keystore/targets_key.pub"))
repository.snapshot.add_verification_key(import_rsa_publickey_from_file("/home/pankhuri/projects/repository/keystore/snapshot_key.pub"))
repository.timestamp.add_verification_key(import_rsa_publickey_from_file("/home/pankhuri/projects/repository/keystore/timestamp_key.pub"))

private_targets_key = import_rsa_privatekey_from_file("/home/pankhuri/projects/repository/keystore/targets_key")
private_snapshot_key = import_rsa_privatekey_from_file("/home/pankhuri/projects/repository/keystore/snapshot_key")
private_timestamp_key = import_rsa_privatekey_from_file("/home/pankhuri/projects/repository/keystore/timestamp_key")


repository.targets.load_signing_key(private_targets_key)
repository.snapshot.load_signing_key(private_snapshot_key)
repository.timestamp.load_signing_key(private_timestamp_key)

repository.timestamp.expiration = datetime.datetime(2015, 10, 28, 12, 8)

repository.targets.compressions = ["gz"]
repository.snapshot.compressions = ["gz"]

repository.write()


