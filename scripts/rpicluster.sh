#!/usr/bin/env bash

PREFIX="$(realpath $(dirname $0))"
SCRIPT_PY="$PREFIX/rpicluster.py"
SLAVE_LIST="$PREFIX/rpicluster.txt"


if [ -e "$SLAVE_LIST" -a ! -f "$SLAVE_LIST" ]; then
    echo "error: Slave list $SLAVE_LIST is not a normal file.  Remove it." >&2
    exit 1
fi

regexp='^ *[0-9]+ *:.*$'
num1=$(wc -l <"$SLAVE_LIST")
num2=$(egrep -c "$regexp" <"$SLAVE_LIST")
if [ "$num1" -eq 0 ]; then
    echo "error: No slaves found in slave list"
    read -p 'Press RETURN to edit the file...'
    $EDITOR "$SLAVE_LIST"
    echo 'Now restart the script to enable the new configuration'
    exit 0
elif [ "$num1" -ne "$num2" ]; then
    echo "error: Slave list must obey this format: \"$regexp\"" >&2
    exit 1
fi

slaves_avail=
slaves_dscr=()
while read line; do
    n=$(echo "$line" | cut -d: -f1 | tr -d '[:space:]')
    dscr=$(echo "$line" | cut -d: -f2- | sed -e 's/^ *//' -e 's/ *$//')
    slaves_avail+=" $n"
    slaves_dscr[$n]="$dscr"
done <"$SLAVE_LIST"


tmp="$(mktemp)"
trap "{ rm -f \"$tmp\"; }" EXIT


control_power() {
    while :; do
        cmd="$SCRIPT_PY"
        for i in $slaves_avail; do
            cmd+=" -i $i"
        done
        stats=($($cmd))

        cmd="dialog --no-tags --cancel-label 'Go up'"
        cmd+=" --extra-button --extra-label 'Refresh'"
        cmd+=" --checklist 'RPiCluster2: Power control' 0 0 0"
        j=0
        for i in $slaves_avail; do
            if [ "${stats[$j]}" -eq 0 ]; then
                stat="off"
            else
                stat="on"
            fi
            cmd+=$(printf " %d \"Slave #%-2d: %s\" %s" "$i" "$i" \
                    "${slaves_dscr[$i]}" "$stat")
            j=$((j+1))
        done

        bash -c "$cmd" 2>"$tmp"
        ret="$?"

        if [ "$ret" -eq 0 ]; then
            # Select button is pressed.
            read en <"$tmp"
            dis=$(echo "$slaves_avail $en" | sed 's/ \+/ /g' | tr -s ' ' '\n' |
                    sort | uniq -u)
            cmd="$SCRIPT_PY"
            for n in $dis; do
                cmd+=" -d $n"
            done
            for n in $en; do
                cmd+=" -e $n"
            done
            bash -c "$cmd"
            ret="$?"
            break
        elif [ "$ret" -eq 3 ]; then
            # Refresh button is pressed.
            continue
        elif [ "$ret" -eq 1 ]; then
            # Exit button is pressed.
            ret=0
            break
        else
            echo "error: Invalid return code from dialog: $ret" >&2
            ret=1
            break
        fi
    done

    return "$ret"
}


select_serial() {
    cmd="dialog --no-tags --ok-label 'Select' --cancel-label 'Go up'"
    cmd+=" --extra-button --extra-label 'Refresh'"
    cmd+=" --radiolist 'RPiCluster2: Serial select' 0 0 0"
    on=$($SCRIPT_PY -i s)
    if [ "$on" -eq "-1" ]; then
        stat="on"
    else
        stat="off"
    fi
    cmd+=" -1 \"Disable serial\" $stat"
    for i in $slaves_avail; do
        if [ "$i" -eq "$on" ]; then
            stat="on"
        else
            stat="off"
        fi
        cmd+=$(printf " %d \"Slave #%-2d: %s\" %s" "$i" "$i" \
                "${slaves_dscr[$i]}" "$stat")
    done

    while :; do
        bash -c "$cmd" 2>"$tmp"
        ret="$?"

        if [ "$ret" -eq 0 ]; then
            # Select button is pressed.
            read tag <"$tmp"
            $SCRIPT_PY -s "$tag"
            ret="$?"
            break
        elif [ "$ret" -eq 3 ]; then
            # Refresh button is pressed.
            continue
        elif [ "$ret" -eq 1 ]; then
            # Exit button is pressed.
            ret=0
            break
        else
            echo "error: Invalid return code from dialog: $ret" >&2
            ret=1
            break
        fi
    done

    return "$ret"
}


main_menu() {
    while :; do
        if service nfs-kernel-server status >&/dev/null; then
            NFSD_STAT=1
        else
            NFSD_STAT=0
        fi

        cmd="dialog --no-tags --ok-label 'Select' --cancel-label 'Exit'"
        cmd+=" --extra-button --extra-label 'Refresh'"
        cmd+=" --menu 'RPiCluster2' 0 0 0"
        cmd+=" power 'Power control'"
        cmd+=" sersel 'Serial select'"
        if [ "$NFSD_STAT" -eq 0 ]; then
            cmd+=" nfsd 'Start NFS server'"
        else
            cmd+=" nfsd 'Stop NFS server'"
        fi
        cmd+=" sercon 'Open serial terminal'"
        cmd+=" edit 'Edit slave list'"

        bash -c "$cmd" 2>"$tmp"
        ret="$?"
        clear

        if [ "$ret" -eq 0 ]; then
            # Select button is pressed.
            read tag <"$tmp"
            case "$tag" in
                power)
                    control_power
                    ret="$?"
                    ;;
                sersel)
                    select_serial
                    ret="$?"
                    ;;
                nfsd)
                    if [ "$NFSD_STAT" -eq 0 ]; then
                        sudo service nfs-kernel-server start
                        ret="$?"
                    else
                        sudo service nfs-kernel-server stop
                        ret="$?"
                    fi
                    ;;
                sercon)
                    picocom -b 115200 /dev/ttyAMA0
                    ret="$?"
                    ;;
                edit)
                    $EDITOR "$SLAVE_LIST"
                    ret="$?"
                    ;;
                *)
                    echo "internal error: Invalid tag: $tag" >&2
                    ret=1
                    ;;
            esac
            break
        elif [ "$ret" -eq 3 ]; then
            # Refresh button is pressed.
            continue
        elif [ "$ret" -eq 1 ]; then
            # Exit button is pressed.
            ret=1
            break
        else
            echo "error: Invalid return code from dialog: $ret" >&2
            ret=1
            break
        fi
    done

    return "$ret"
}

while main_menu; do
    :
done
