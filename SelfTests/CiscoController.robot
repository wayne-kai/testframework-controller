*** Settings ***
Documentation       Test CiscoController functionality.
Variables           ../Variables/common.yaml
Resource            ../Resources/Robot/CiscoRobotCommon.robot
Test Setup          Initialise Cisco Controller Settings

*** Keywords ***
Initialise Cisco Controller Settings
    Initialise Controller Settings
    Set Legit Credential
    Set Config Credentials  &{SUPER_ACCOUNT}[user]  &{SUPER_ACCOUNT}[pass]  &{SUPER_ACCOUNT}[enable]


*** Test Cases ***
Test Run Command And Get Output
    [Tags]  command
    Run Command And Get Output  show clock


Test Run Test Command
    [Tags]  command
    ${cmd}=                 Create Test Cmd     sh proc | inc TCP
    Add Test Cmd Criteria   ${cmd}  should_contain=TCP Protocols
    Run Test Cmd            ${cmd}


Test Configure Invalid Types
    [Tags]  configure   error
    Run Keyword And Expect Error    ValueError: Configure Router: Unknown auth type     Configure   DUMMY


Test Configure
    [Tags]  configure
    Configure   CONF_LOCAL_UIDPASS_ADMIN
    Configure   CONF_LOCAL_UIDPASS_USR
    Configure   CONF_LOCAL_PASS_ADMIN
    Configure   CONF_LOCAL_PASS_USR
    Configure   CONF_LOCAL_NOUIDPASS_ADMIN
    Configure   CONF_LOCAL_NOUIDPASS_USR
    Configure   CONF_REMOTE_UIDPASS_ADMIN
    Configure   CONF_REMOTE_UIDPASS_USR
    Configure   CONF_RESET


Test Retrieve Logs
    [Tags]  logs
    Start Tracking Logs             ${LOG_CHECK_TO_TRACK}
    Run Command And Get Output  show ip int brief
    Retrieve Logs                   ${LOG_CHECK_TO_TRACK}


Test Reboot
    [Tags]  reboot
    Reboot


Test Replace Firmware
    [Tags]  firmware
    Replace Firmware        ${LEGIT_FIRMWARE_PATH}
    ${cmd}=                 Create Test Cmd     sh flash | inc ${FIRMWARE}
    Add Test Cmd Criteria   ${cmd}  should_contain=${FIRMWARE}
    Run Test Cmd            ${cmd}

