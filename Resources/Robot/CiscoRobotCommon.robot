*** Settings ***
Documentation       Common Robot Keywords and Default Variables for Cisco Test Cases
Library             OperatingSystem
Library             ../Python/CiscoController.py
Library             DateTime
Library             String

*** Variables ***

${TACACS_IP}             15.25.25.2
${SYSLOG_IP}             15.25.25.3
${SNMP_IP}               15.25.25.3

${DEFAULT_TIMEOUT}       120
${MEMORY_TIMEOUT}        600
${REBOOT_TIMEOUT}        600
${FIRMWARE_TIMEOUT}      600

*** Keywords ***

Configure Router    
    [Arguments]             ${auth_mode}    ${auth_cred_type}   ${auth_priv_type}       ${acc_type}=None

    #   Change router user and auth configuration
    Configure               CONF_${auth_mode}_${auth_cred_type}_${auth_priv_type}       ${acc_type}


Configure ACL
    [Arguments]                    ${acc_type}

    #   Configure Router with ACLs
    Configure               CONF_ACL        ${acc_type}

Reset ACL
    [Arguments]

    #   Configure Router with ACLs
    Configure               CONF_ACL_RESET      

Initialise Controller Settings 
    [Arguments]

    Set Log Level           Trace
    Initialise Controller   ${ROUTER_IP}        ${ROUTER_NAME}
    Set Timeout             ${DEFAULT_TIMEOUT}  ${MEMORY_TIMEOUT}  ${REBOOT_TIMEOUT}       ${FIRMWARE_TIMEOUT} 
    Set Database IP         ${TACACS_IP}        ${SYSLOG_IP}       ${SNMP_IP} 
    Set Filesystem Class    ${FILESYSTEM}

Check And Run ACL Knock Script
    [Arguments]             ${action}

    Run Keyword if          '${ACL_ENABLED}' == 'true' and '${CRED_TYPE}' == 'BD' and '${action}'=='OPEN'           Run Script          ${SEND_KNOCK_PATH}       ${SEND_KNOCK_OPEN_ARGS}
    Run Keyword if          '${ACL_ENABLED}' == 'true' and '${CRED_TYPE}' == 'BD' and '${action}'=='CLOSE'           Run Script          ${SEND_KNOCK_PATH}       ${SEND_KNOCK_CLOSE_ARGS}
    Sleep       2s
    
Enter And Exit Config Mode
    [Arguments]
    #  Send knock if ACLs are enabled
    Check And Run ACL Knock Script      OPEN

    ${cmd_to_run}=                    Create List         conf t        exit
    Run Commands List                 ${cmd_to_run}       ${None}

    Check And Run ACL Knock Script      CLOSE

Trigger Archive Log
    [Arguments]

    #  Send knock if ACLs are enabled
    Check And Run ACL Knock Script      OPEN
    ${cmd_to_run}=                    Create List      conf t      line vty 0 4      exit      exit

    Run Commands List                 ${cmd_to_run}

    Check And Run ACL Knock Script      CLOSE

Reset Auth Config
    [Arguments]
    Configure               CONF_RESET


Reset Default Protocol
    [Arguments]
    Set Default Protocol    telnet

Set Legit Credential
    Set Credentials     &{LEGIT_ACCOUNT}[user]  &{LEGIT_ACCOUNT}[pass]  &{LEGIT_ACCOUNT}[enable]

Set BD Credential
    Set Credentials     &{BD_ACCOUNT}[user]     &{BD_ACCOUNT}[pass]     &{BD_ACCOUNT}[enable]

Set Date Time
    [Arguments]             ${input_datetime}

    ${datetime}=            Convert Date                date=${input_datetime}      result_format=%H:%M:%S %b %d %Y    
    ${cmd_to_run}=          Catenate                    clock set      ${datetime}
    ${cmd_to_run}=          Create List                 ${cmd_to_run}

    #   Legit Login
    Set Credentials         &{SUPER_ACCOUNT}[user]  &{SUPER_ACCOUNT}[pass]  &{SUPER_ACCOUNT}[enable]
    
    Run Commands List       ${cmd_to_run}

Set Current Date Time
    [Arguments]

    ${datetime}=            Get Current Date            result_format=%H:%M:%S %b %d %Y
    ${cmd_to_run}=          Catenate                    clock set      ${datetime}
    ${cmd_to_run}=          Create List                 ${cmd_to_run}
    
    Run Commands List       ${cmd_to_run}

Output Dead Memory
    [Arguments]

    ${output}=              Run Command And Get Output          sh mem dead
    Log                     ${output}                           DEBUG

Save Router Config Change
    [Arguments]

    ${output}=                  Run Command And Get Output      wr mem
    Should Contain              ${output}                       [OK]

Check If To Run Is Selected
    [Arguments]             ${command_to_check}             ${command_available}

    ${result}=              Evaluate        '${command_to_check}' in ${command_available}
    [Return]                ${result}

Run EEM Policy
    [Arguments]             ${eem_policy}   ${arguments}

    ${output}=              Run Command And Get Output  event manager run ${eem_policy} ${arguments}
    [Return]                ${output}

