// A minimal test harness based on https://stackoverflow.com/a/19179564, for
// the purpose of learning how the ioctl works so I can work it into the rest
// of the Cloud Copycat Python code.

#include <fcntl.h>
#include <limits.h>
#include <linux/cdrom.h>
#include <stdio.h>
#include <sys/ioctl.h>
#include <unistd.h>

int main(int argc, char **argv) {
	if (argc < 2) {
		printf("need argument\n");
		return 1;
	}

	int fd = open(argv[1], O_RDONLY | O_NONBLOCK);
	if (fd < 0) {
		perror("open drive");
		return 1;
	}

	int retcode = 0;
	int result = ioctl(fd, CDROM_DRIVE_STATUS, CDSL_NONE);

	switch(result) {
		case CDS_NO_INFO:
			printf("no info\n");
			break;
		case CDS_NO_DISC:
			printf("no disc\n");
			break;
		case CDS_TRAY_OPEN:
			printf("tray open\n");
			break;
		case CDS_DRIVE_NOT_READY:
			printf("drive not ready\n");
			break;
		case CDS_DISC_OK:
			printf("disc ok\n");
			break;
		default:
			perror("drive");
			retcode = 1;
			break;
	}

	close(fd);
	return retcode;
}
