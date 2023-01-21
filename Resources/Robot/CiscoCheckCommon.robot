*** Settings ***
Documentation       Cisco Tools Check Keywords
Resource            CiscoRobotCommon.robot
Library             ../Python/RSALib.py

*** Variables ***

*** Keywords ***
Check For Custom Public Key
    [Arguments]      ${keyfilePath}     ${exist}=${true}    ${command}=show software authenticity keys

    Log To Console          ${\n}Checking for Custom Public Key in Cisco Router

    #   Obtained the modulus from the public key file
    ${modulusStr}=                  Get Modulus From Keyfile            ${keyfilePath}

    Check For Public Key            ${modulusStr}     ${exist}      ${command}

Check For Public Key
    [Arguments]      ${modulusStr}     ${exist}         ${command}

    #   Construct the regex match pattern for the modulus string
    ${regexPatternForModulus}=      Construct Match Pattern             ${modulusStr}

    #   Obtained the modulus from the router
    ${pubKeyOutput}=                Run Command And Get Output          ${command}

    Run Keyword If          ${exist} == ${true}     Run Keyword And Continue on Failure         Should Match Regexp          ${pubKeyOutput}         ${regexPatternForModulus}           Cannot find [${modulusStr}]. Not inserted?     ${false}
    Run Keyword If          ${exist} == ${false}    Run Keyword And Continue on Failure         Should Not Match Regexp      ${pubKeyOutput}         ${regexPatternForModulus}           Found [${modulusStr}]. Not removed?     ${false}

Check Memory Alignment And Spurious Irregularity
    [Arguments]
    
    Check And Run ACL Knock Script      OPEN

    #   Execute command
    ${show_alignment_output}=  Run Command And Get Output      show alignment

    ${contains}=                Evaluate        'Invalid input detected at' in '''${show_alignment_output}'''

    Run Keyword If   ${contains} == ${true}          Log     "show alignment" Command is not available in ${TEST NAME}     WARN

    #   Ensure that the following message appears
    #   Note: If anything else appears, it would appear that the memory has been tampered with
    Run Keyword If   ${contains} == ${false}         Run Keywords
    ...     Should Contain      ${show_alignment_output}        No alignment data has been recorded
    ...     AND     Should Contain      ${show_alignment_output}        No spurious memory references have been recorded

    Check And Run ACL Knock Script      CLOSE

Check No Config Change Banner
    [Arguments]                     ${user_name}      

    Check And Run ACL Knock Script      OPEN

    ${output}=                      Run Command And Get Output      sh run
    Run Keyword And Continue on Failure             Should Not Contain              ${output}                       No configuration change since last restart
    Run Keyword And Continue on Failure             Should Not Match Regexp         ${output}                       [\\s\\S]*Last configuration change at [a-zA-Z0-9 :]{17,} by ${user_name}[\\s\\S]*

    Check And Run ACL Knock Script      CLOSE

Check No Config Change
    [Arguments]

    Check And Run ACL Knock Script      OPEN
    
    ${sh_run_cfg}               Create Test Cmd     sh run
    Add Test Cmd Criteria       ${sh_run_cfg}       should_contain=No configuration change since last restart

    Run Keyword And Continue on Failure             Run Test Cmd                ${sh_run_cfg}

    Check And Run ACL Knock Script      CLOSE

Check Last Config Change
    [Arguments]                 ${user_name}

    Check And Run ACL Knock Script      OPEN

    ${sh_run_cfg}               Create Test Cmd     sh run
    Add Test Cmd Criteria       ${sh_run_cfg}       should_match_regex=[\\s\\S]*Last configuration change at [a-zA-Z0-9 :]{17,} by ${user_name}[\\s\\S]*

    Run Keyword And Continue on Failure             Run Test Cmd                ${sh_run_cfg}

    Check And Run ACL Knock Script      CLOSE

Check Reload Config Change Prompt
    [Arguments]         ${expect_prompt}

    ${check_reload}     Create Test Cmd                     reload
    Run Keyword If      '${expect_prompt}' == 'Yes'         Run Keywords
    ...                 Add Test Cmd Criteria               ${check_reload}             should_begin_with=System configuration has been modified
    ...                 AND                                 Add Test Cmd Criteria       ${check_reload}     should_contain=System configuration has been modified
    Run Keyword If      '${expect_prompt}' == 'No'          Run Keywords
    ...                 Add Test Cmd Criteria               ${check_reload}             should_begin_with=Proceed with reload?
    ...                 AND                                 Add Test Cmd Criteria       ${check_reload}     should_contain=Proceed with reload?

    Check And Run ACL Knock Script      OPEN

    Run Keyword And Continue on Failure                     Run Test Cmd                ${check_reload}

    Check And Run ACL Knock Script      CLOSE