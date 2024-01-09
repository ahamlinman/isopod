# Isopod

Isopod is a Linux daemon that watches a CD-ROM drive, rips the discs inserted
into it, and then rsyncs the resulting ISOs to remote storage in the background.
While it works on any system with the required dependencies, it's designed for
use on a Raspberry Pi with a special E-Ink status display, to support easy
operation by non-technical users.

**For technical reasons, Isopod cannot rip audio CDs or copy-protected media.**
With discs that Isopod _does_ support, you are fully responsible for ensuring
that your use of Isopod complies with all laws, regulations, etc. that you may
be subject to. (My original use case for Isopod is to help back up home videos
that were previously transferred from 8mm tape to DVD-Rs that are slowly but
surely [rotting away](https://en.wikipedia.org/wiki/Disc_rot).)

Isopod is a relatively new personal project, and is largely undocumented.
Further information about Isopod and the terminal hardware may be provided in
the future.
