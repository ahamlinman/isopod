# Isopod Target

This is a minimal container image for an rsync daemon, which you can use to run
Isopod with **unencrypted** rsync transfers. This may be useful for testing, or
_perhaps_ in scenarios where the encryption and authentication normally
provided by SSH are provided by other means.

To use the image:

- Run with a read-only root filesystem, and a persistent volume mounted at
  `/mnt/isopod-target`.
- Run with a non-root user and group. This user and group will own all files
  written to the volume.
- Forward a host port to the container's port 873. Consider listening on a
  loopback or VPN address only.
