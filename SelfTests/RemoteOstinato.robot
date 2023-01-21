*** Settings ***
Documentation   Test controlling a remote Ostinato drone on a VM via ESXI
Library         ../Resources/Python/RemoteOstinatoController.py
Variables       ../Variables/common.yaml
Test Template   Test Remote Ostinato Drone
Default Tags    ostinato    drone   remote  self-test


*** Keywords ***
Test Remote Ostinato Drone
    [Arguments]     ${testnet}
    Initialise Remote Traffic Generator     ${ESXI.host}    ${ESXI.user}    ${ESXI.password}    ${REMOTE_TRAFFIC_GENERATOR.host}    ${REMOTE_TRAFFIC_GENERATOR.user}    ${REMOTE_TRAFFIC_GENERATOR.password}
    Initialise Generator In Network     ${testnet}
    Configure Traffic Generator         ${testnet}  ${OSTINATO.portid}  ${OSTINATO.target}  128
    Start Traffic Generator             ${testnet}  ${OSTINATO.portid}
    Stop Traffic Generator              ${testnet}  ${OSTINATO.portid}
    Clear Traffic Generator             ${testnet}  ${OSTINATO.portid}


*** Test Cases ***  TESTNET
Testnet 1        Testnet 1
Testnet 3        Testnet 3
