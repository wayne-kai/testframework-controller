*** Settings ***
Documentation       Keywords for Cisco Local Log Cleaner
Variables           ../../Variables/common.yaml
Variables           ../../Variables/Cisco-Log-Cleaner-common.yaml
Library             String
Library             Collections

*** Keywords ***

### Test Setup Check Keyword(s) ###

Cisco Log Cleaner Configuration Check
    [Arguments]

    #   These are required keywords for the Cisco Log Cleaner test
    Variable Should Exist   ${CLEANER_INJECT_PATH}              Required "CLEANER_INJECT_PATH" is missing
    Variable Should Exist   ${CLEANER_INJECT_UNDO_PATH}         Required "CLEANER_INJECT_UNDO_PATH" is missing
    Variable Should Exist   ${SH_HIST_ALL_CLEANER_CMD}          Required "SH_HIST_ALL_CLEANER_CMD" is missing
    Variable Should Exist   ${SH_LOG_CLEANER_CMD}               Required "SH_LOG_CLEANER_CMD" is missing
    Variable Should Exist   ${ARCH_LOG_CONFIG_ALL_CLEANER_CMD}  Required "ARCH_LOG_CONFIG_ALL_CMD" is missing

### Setup Keyword(s) ###

Cisco Log Cleaner Install
    [Arguments]             ${install_firmware}=${False}        ${firmware}=${None}          ${reboot}=${False}  

    #   To ensure that the required variables are available first before performing the installation
    Cisco Log Cleaner Configuration Check

    #   Install firmware first    
    #   NOTE: To ensure that the required firmware is installed first before everything starts
    Run Keyword If          ${install_firmware} == ${True}                                      Replace Firmware        ${firmware}    ${CORRUPTED_PATH}
    Run Keyword If          ${install_firmware} == ${True} or ${reboot} == ${True}              Reboot

    Set Test Variable       ${log_cleaner_installed}    ${True}
    Install Mem Inject      ${CLEANER_INJECT_PATH}      No

Cisco Log Cleaner Uninstall
    [Arguments]

    Set Test Variable       ${log_cleaner_installed}            ${False}
    Install Mem Inject      ${CLEANER_INJECT_UNDO_PATH}         Yes

### Check Keyword(s) ###

Cisco Log Cleaner Check Logs Does Not Exist
    [Arguments]             ${lines}                ${lines_to_find}

    :FOR     ${line_removed}         IN      @{lines_to_find}
    \     Run Keyword and Continue On Failure         List Should Not Contain Value       ${lines}        ${line_removed}  

### Functionality Keyword(s) ###

##  Show History All ##

Cisco Log Cleaner Remove Show History All Entry
    [Arguments]             ${str_pattern}                  ${remove_all}=True

    Run Keyword If          ${log_cleaner_installed} == False        Fail                Log Cleaner is not installed

    Log                     Execute Show History All Cleaner Command ...        INFO

    ${cmd_args}=            Set Variable If
    ...                     '${remove_all}' == 'False'              ${SH_HIST_ALL_ARG}${FLAG_RM_FIRST_OCCURRENCE} ${str_pattern}
    ...                     '${remove_all}' == 'True'               ${SH_HIST_ALL_ARG}${FLAG_RM_ALL_OCCURRENCE} ${str_pattern}

    ${cmd_to_run}=          Create List                         ${SH_HIST_ALL_CLEANER_CMD}       ${cmd_args}

    Run Commands List       ${cmd_to_run}   no_shell_prompt=${true}

##  Show Log ##

Cisco Log Cleaner Remove Show Log Entry
    [Arguments]             ${str_pattern}                  ${remove_all}=True

    Run Keyword If          ${log_cleaner_installed} == False        Fail                Log Cleaner is not installed

    Log                     Execute Show Log Cleaner Command ...        INFO
   
    ${cmd_args}=            Set Variable If
    ...                     '${remove_all}' == 'False'              ${SH_LOG_ARG}${FLAG_RM_FIRST_OCCURRENCE} ${str_pattern}
    ...                     '${remove_all}' == 'True'               ${SH_LOG_ARG}${FLAG_RM_ALL_OCCURRENCE} ${str_pattern}

    ${cmd_to_run}=          Create List                             ${SH_LOG_CLEANER_CMD}       ${cmd_args}

    Run Commands List       ${cmd_to_run}   no_shell_prompt=${true}  

##  Show Archive Log Config All ##

Cisco Log Cleaner Remove Show Archive Log Config All Entry
    [Arguments]             ${entry_id}

    Log                     Execute Show Archive Log Config All Cleaner Command ...        INFO

    #   Execute the cleaner command
    ${cmd_to_run}=          Create List                             ${ARCH_LOG_CONFIG_ALL_CLEANER_CMD} ${entry_id}
    Run Commands List       ${cmd_to_run}   no_shell_prompt=${true}