#cython: language_level=3

from enum import Enum

cdef extern from "<linux/cdrom.h>":
    cdef int _CDROM_DRIVE_STATUS "CDROM_DRIVE_STATUS"
    cdef int _CDSL_NONE "CDSL_NONE"
    cdef int _CDS_NO_INFO "CDS_NO_INFO"
    cdef int _CDS_NO_DISC "CDS_NO_DISC"
    cdef int _CDS_TRAY_OPEN "CDS_TRAY_OPEN"
    cdef int _CDS_DRIVE_NOT_READY "CDS_DRIVE_NOT_READY"
    cdef int _CDS_DISC_OK "CDS_DISC_OK"

CDROM_DRIVE_STATUS = _CDROM_DRIVE_STATUS
CDSL_NONE = _CDSL_NONE

class DriveStatus(Enum):
    NO_INFO = _CDS_NO_INFO
    NO_DISC = _CDS_NO_DISC
    TRAY_OPEN = _CDS_TRAY_OPEN
    DRIVE_NOT_READY = _CDS_DRIVE_NOT_READY
    DISC_OK = _CDS_DISC_OK
