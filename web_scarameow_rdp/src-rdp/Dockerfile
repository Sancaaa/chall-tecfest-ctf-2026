FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# XFCE minimal (tanpa efek/compositor berat) + xrdp + sudo + python3
#
# PATCH (fix layar hitam):
# - xserver-xorg-legacy + Xwrapper.config allowed_users=anybody
#   -> tanpa ini, Xorg di dalam container sering menolak jalan untuk user
#      non-console ("Only console users are allowed to run the X server"),
#      sesi RDP konek tapi X server mati -> layar hitam.
# - x11-xserver-utils + dbus-x11 dipastikan ada untuk startwm.sh
# - adwaita-icon-theme ditambahkan supaya XFCE tidak gagal render tema
RUN apt-get update && apt-get install -y --no-install-recommends \
    xrdp \
    xorgxrdp \
    xserver-xorg-legacy \
    x11-xserver-utils \
    xfce4 \
    xfce4-terminal \
    adwaita-icon-theme \
    sudo \
    python3 \
    dbus-x11 \
    iputils-ping \
    && apt-get clean && rm -rf /var/lib/apt/lists/* \
    && sed -i 's/allowed_users=.*/allowed_users=anybody/' /etc/X11/Xwrapper.config \
    && sed -i 's/needs_root_rights=.*/needs_root_rights=yes/' /etc/X11/Xwrapper.config

# User RDP sesuai "notes" yang bocor dari SQLi
RUN useradd -m -s /bin/bash sadmin \
    && echo "sadmin:S3rv3r_N0t3s_2026!" | chpasswd \
    && echo "xfce4-session" > /home/sadmin/.xsession \
    && chown sadmin:sadmin /home/sadmin/.xsession \
    && chmod 644 /home/sadmin/.xsession

# Tool "admin" yang sengaja bisa dijalankan sadmin lewat sudo tanpa password,
# tapi ada filter karakter yang bisa di-bypass (mirip gaya HTB "Jarvis").
RUN mkdir -p /opt/admin-tools
COPY simpler.py /opt/admin-tools/simpler.py
RUN chmod 755 /opt/admin-tools/simpler.py

RUN echo "sadmin ALL=(root) NOPASSWD: /usr/bin/python3 /opt/admin-tools/simpler.py*" \
    > /etc/sudoers.d/sadmin-tools \
    && chmod 440 /etc/sudoers.d/sadmin-tools

# Flag — bukti privesc berhasil sampai root
RUN echo "TecFest26{pr1v3sc_v14_5ud0_pyth0n_f1lt3r_byp4ss_m30w}" > /root/flag.txt \
    && chmod 600 /root/flag.txt

# Flag user (akses RDP awal)
COPY user.flag /home/sadmin/user.flag
RUN chown sadmin:sadmin /home/sadmin/user.flag && chmod 644 /home/sadmin/user.flag

RUN mkdir -p /var/run/sshd /run/xrdp

# PATCH (fix layar hitam):
# startwm.sh lama hanya "startxfce4" polos, tanpa dbus session yang benar
# dan tanpa compositor xfwm4 dimatikan -> di container tanpa GPU, ini sering
# membuat XFCE gagal render (layar hitam) meskipun proses tidak crash.
RUN printf '#!/bin/sh\n\
unset DBUS_SESSION_BUS_ADDRESS\n\
xfconf-query -c xfwm4 -p /general/use_compositing -s false 2>/dev/null || true\n\
exec dbus-launch --exit-with-session startxfce4\n' > /etc/xrdp/startwm.sh \
    && chmod 755 /etc/xrdp/startwm.sh

EXPOSE 3389

CMD ["bash", "-c", "service dbus start; xrdp-sesman; xrdp --nodaemon"]
