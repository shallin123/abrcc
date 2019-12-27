#!/bin/bash
LOG=runner
source ./env.sh

OUT_DIR=$CHROMIUM_DIR/src/$TARGET

HOST=127.0.0.1
PORT=6121
SITE=www.example.org

TC=/sbin/tc
BW=""
DELAY=""
BURST="20000"
CERTS=""
DASH_ARGS=""

function build {
    log "Building $1"
    run_cmd $TOOLS_DIR/ninja -C $OUT_DIR $1
}

function setup_certs {
    if [ -z "$CERTS" ] ; then 
        log "Skipping certs setup."    
    else
        log "Setup certs..."
        generate_certs
        install_certs
        log "Certs setup."
    fi
}

function set_network_conditions {
    log "Setting network conditions.."
    
    log "Resetting qdiscs..."
    priv_run_cmd $TC qdisc del dev lo root

    if [ -z "$BW" ] && [ -z "$DELAY" ] ; then 
        return    
    fi 
    
    local cmd="${TC} qdisc add dev lo parent 1:3 handle 30: tbf"
    if [ ! -z "$BW" ] ; then  
        cmd="${cmd} rate ${BW}mbit" 
    fi
    if [ ! -z "$DELAY" ]; then 
        cmd="${cmd} latency ${DELAY}ms"
    fi
    cmd="${cmd} burst ${BURST}" 

    priv_run_cmd $TC qdisc add dev lo root handle 1: prio
    
    echo "[running] $cmd"
    eval $cmd

    log "Throttling bandwidth on port $PORT"
    priv_run_cmd $TC filter add dev lo protocol ip parent 1:0 prio 3 u32 match ip sport $PORT 0xffff flowid 1:3

    log "Network conditions set."
}

function build_dash_client_npm {
    log "Building dash client..."
    pushd $DIR/../dash > /dev/null

    run_cmd npm run build $DASH_ARGS 
    
    SRC=$DIR/../dash
    DST=$DIR/sites/$SITE
    run_cmd rm -rf $DST/dist
    run_cmd cp -r $SRC/dist $DST
    run_cmd rm -rf $DST/index.html
    run_cmd cp $SRC/index.html $DST

    popd > /dev/null
    log "Dash client built."
}

function quic_server {
    build_dash_client_npm
    build dash_server

    setup_certs
    set_network_conditions

    run_cmd $OUT_DIR/dash_server \
        --v=1 \
        --quic_config_path=$DIR/config.json \
        --port=$PORT \
        --certificate_file=$CERTS_PATH/out/leaf_cert.pem \
        --key_file=$CERTS_PATH/out/leaf_cert.pkcs8 
}

function quic_client {
    build quic_client
    run_cmd $OUT_DIR/quic_client \
        --disable_certificate_verification=True \
        --host=$HOST \
        --port=$PORT \
        $SITE
}

function quic_chrome {
    RED_PORT=443
    google-chrome-stable \
        --v=1 \
        --user-data-dir=/tmp/chrome-profile \
        --no-proxy-server \
        --enable-quic \
        --origin-to-force-quic-on=$SITE:$RED_PORT \
        --ignore-certificate-errors \
        --allow-running-insecure-content \
        --enable-features=NetworkService \
        --incognito \
        --host-resolver-rules='MAP www.example.org:443 127.0.0.1:6121' \
        https://$SITE
}

function usage() {
    echo "Usage: $0 [OPTION]..."
    echo "Quic runner."

    echo -e "\nOptions: "
    printf "\t %- 30s %s\n" "-s | --server" "Run a quic server."
    printf "\t %- 30s %s\n" "-c | --client" "Run a quic client."
    printf "\t %- 30s %s\n" "-b | --build" "Build quic client and server."
    printf "\t %- 30s %s\n" "--chrome" "Run a quic client in Chrome."
    printf "\t %- 30s %s\n" "--port [int]" "Change the port. (default 6121)"
    printf "\t %- 30s %s\n" "--site [url]" "Change the site. (default www.example.org)"
    printf "\t %- 30s %s\n" "--bw [int]" "Change connection bandwidth in mbit."
    printf "\t %- 30s %s\n" "(--latency | --delay) [int]" "Change connection latency in ms."
    printf "\t %- 30s %s\n" "--burst [int]" "Change the burst. (default 20000)"
    printf "\t %- 30s %s\n" "--certs" "Regenerate and install server certificates."
    printf "\t %- 30s %s\n" "-d | --dash" "Pass a command line argument to dash."

    echo -e "\nExamples: "
    printf "\t %- 30s %s\n" "sudo run.sh --bw 2 --latency 100 -s --site www.example.org"
    printf "\t %- 30s %s\n" "run.sh -s"
    printf "\t %- 30s %s\n" "run.sh -c --port 6333 --site www.example.org"
}


function parse_command_line_options() {
    while [ "${1:-}" != "" ]; do
        case $1 in
            -b | --build)
                build net
                build quic_client
                build dash_server
                exit 0
                ;;
            -c | --client)
                FUNC=quic_client
                ;;
            -s | --server)
                FUNC=quic_server
                ;;
            --chrome)
                shift
                FUNC=quic_chrome
                ;;
            --host)
                shift
                HOST=$1
                ;;
            --port)
                shift
                PORT=$1
                ;;
            --site)
                shift
                SITE=$1
                ;;
            --bw)
                shift 
                BW=$1
                ;;
            --burst)
                shift 
                BURST=$1
                ;;
            --latency | --delay)
                shift 
                DELAY=$1
                ;;
            --certs)
                CERTS="yes"
                ;;
            -d | --dash)
                shift
                DASH_ARGS="${DASH_ARGS} $1"
                ;;
            -h | --help )
                usage
                exit 0
                ;;
            * )
                usage
                exit 1
        esac

        shift
    done
}

FUNC=usage
parse_command_line_options "$@"
$FUNC
