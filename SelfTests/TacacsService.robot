*** Settings ***
Documentation   Test controlling a TACACS service VM via ESXI
Library         ../Resources/Python/TacacsController.py
Variables       ../Variables/common.yaml
Default Tags    tacacs  self-test
Test Setup      Initialise Tacacs Controller For Test


*** Keywords ***
Tacacs Service Should Be Running
    ${is_running} =     Is Tacacs Service Running
    Should Be True      ${is_running}

Tacacs Service Should Not Be Running
    ${is_running} =     Is Tacacs Service Running
    Should Not Be True  ${is_running}

Initialise Tacacs Controller For Test
    Initialise Tacacs Controller    ${ESXI.host}    ${ESXI.user}    ${ESXI.password}    ${TACACS.host}  ${TACACS.user}  ${TACACS.password}

*** Test Cases ***
Get Tacacs Service Process While Service is Running
    Ensure Tacacs Service Is Running
    ${process} =        Get Tacacs Service Process
    Log                 ${process}
    Log                 PID of Tacacs Service is ${process.pid}

Stopping And Starting Tacacs Service
    Stop Tacacs Service
    Tacacs Service Should Not Be Running
    Start Tacacs Service
    Tacacs Service Should Be Running

Restarting Tacacs Service
    Restart Tacacs Service
    Tacacs Service Should Be Running

Restarting Tacacs Service After Stopping
    Stop Tacacs Service
    Tacacs Service Should Not Be Running
    Restart Tacacs Service
    Tacacs Service Should Be Running
