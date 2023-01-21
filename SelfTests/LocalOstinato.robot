*** Settings ***
Documentation   Test controlling an Ostinato drone on the local host
Library         ../Resources/Python/OstinatoController.py
Variables       ../Variables/common.yaml
Default Tags    ostinato    drone   local   self-test

*** Variables ***
${LOCAL_PORTID}     3

*** Test Cases ***
Test Ostinato Local
    Configure Streams   ${LOCAL_PORTID}     ${OSTINATO.target}
    Start Transmit      ${LOCAL_PORTID}
    Stop Transmit       ${LOCAL_PORTID}
    Delete Streams      ${LOCAL_PORTID}

