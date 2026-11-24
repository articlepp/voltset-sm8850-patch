/* vsetns: private mount-namespace wrapper for VoltSet.
 * Creates a new mount namespace, makes / private (no propagation to the
 * parent namespace), mounts debugfs, then execs the given command.
 * The debugfs mount is invisible to every other process and disappears
 * when the command exits. */
#define _GNU_SOURCE
#include <sched.h>
#include <sys/mount.h>
#include <unistd.h>
#include <stdio.h>

int main(int argc, char **argv) {
    if (argc < 2) { fprintf(stderr, "usage: vsetns CMD [ARG...]\n"); return 2; }
    if (unshare(CLONE_NEWNS) != 0) { perror("vsetns: unshare"); return 3; }
    if (mount("none", "/", NULL, MS_REC | MS_PRIVATE, NULL) != 0) {
        perror("vsetns: make-private"); return 4;
    }
    mount("debugfs", "/sys/kernel/debug", "debugfs", 0, NULL);
    execv(argv[1], &argv[1]);
    perror("vsetns: exec");
    return 5;
}
