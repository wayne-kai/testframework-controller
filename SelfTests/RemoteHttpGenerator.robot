*** Settings ***
Documentation   Test controlling a remote HTTP generator on a VM via ESXI
Library         ../Resources/Python/RemoteHttpGenerator.py
Variables       ../Variables/common.yaml
Test Template   Test Remote Http Generator
Default Tags    http-generator  remote  self-test


*** Keywords ***
Test Remote Http Generator
    [Arguments]     ${testnet}
    Initialise Remote Http Generator    ${ESXI.host}    ${ESXI.user}    ${ESXI.password}    ${REMOTE_TRAFFIC_GENERATOR.host}    ${REMOTE_TRAFFIC_GENERATOR.user}    ${REMOTE_TRAFFIC_GENERATOR.password}
    Remote Generate Http Traffic        ${HTTP_GENERATOR.target}    ${testnet}  ${HTTP_GENERATOR.connections}
    Run Keyword and Expect Error        RemoteHttpGeneratorError: Error executing*      Remote Generate Http Traffic    ${HTTP_GENERATOR.target}/invalid    ${testnet}  ${HTTP_GENERATOR.connections}
    Run Keyword and Expect Error        *ValueError: unknown url type: 192.168.99.99    Remote Generate Http Traffic    192.168.99.99   ${testnet}  1

*** Test Cases ***  TESTNET
Testnet 1        Testnet 1
Testnet 3        Testnet 3
