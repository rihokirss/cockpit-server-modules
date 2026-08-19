#!/bin/sh
set -eu

if [ "$(id -u)" -ne 0 ]; then
    echo "Run this installer as root (sudo ./install.sh …)." >&2
    exit 1
fi

if [ "$#" -eq 0 ]; then
    echo "Usage: $0 certificates|reverseproxy|samba-ad|radius […]" >&2
    exit 1
fi

root_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
install -d -m 0755 /usr/local/share/cockpit /usr/local/libexec

install_ui() {
    source_dir=$1
    target_name=$2
    install -d -m 0755 "/usr/local/share/cockpit/$target_name"
    install -m 0644 "$source_dir/index.html" "$source_dir/app.js" "$source_dir/style.css" "$source_dir/manifest.json" "/usr/local/share/cockpit/$target_name/"
}

for module in "$@"; do
    case "$module" in
        certificates)
            source_dir="$root_dir/cockpit-certificates"
            install_ui "$source_dir" certificates
            install -m 0755 "$source_dir/cockpit-certificates-helper" /usr/local/libexec/cockpit-certificates-helper
            install -d -m 0755 /etc/letsencrypt/renewal-hooks/deploy
            install -m 0755 "$source_dir/cockpit-certificates-renew-hook" /etc/letsencrypt/renewal-hooks/deploy/cockpit-certificates
            ;;
        reverseproxy)
            source_dir="$root_dir/cockpit-reverseproxy"
            install_ui "$source_dir" reverseproxy
            install -m 0755 "$source_dir/cockpit-reverseproxy-helper" /usr/local/libexec/cockpit-reverseproxy-helper
            ;;
        samba-ad)
            source_dir="$root_dir/cockpit-samba-ad"
            install_ui "$source_dir" samba_ad
            install -m 0755 "$source_dir/cockpit-samba-ad-helper" /usr/local/libexec/cockpit-samba-ad-helper
            ;;
        radius)
            source_dir="$root_dir/cockpit-radius"
            install_ui "$source_dir" radius
            install -m 0755 "$source_dir/cockpit-radius-helper" /usr/local/libexec/cockpit-radius-helper
            install -m 0755 "$source_dir/cockpit-radius-ntlm-auth" /usr/local/libexec/cockpit-radius-ntlm-auth
            ;;
        *)
            echo "Unknown module: $module" >&2
            exit 1
            ;;
    esac
done

echo "Cockpit modules installed. Refresh the Cockpit web interface."
