*** Settings ***
Documentation   Test calling the HTTP generator on the local host
Library         ../Resources/Python/HttpGenerator.py
Variables       ../Variables/common.yaml
Default Tags    http-generator  local   self-test

*** Variables ***

*** Test Cases ***
Locally Generate HTTP Traffic
    Generate Http Get Traffic   ${HTTP_GENERATOR.target}    ${HTTP_GENERATOR.connections}

Handle Invalid Http Host
    Run Keyword and Expect Error    IOError: ${HTTP_GENERATOR.connections} HTTP requests failed     Generate Http Get Traffic   ${HTTP_GENERATOR.target}/invalid    ${HTTP_GENERATOR.connections}

Handle Invalid URL
    Run Keyword and Expect Error    ValueError: unknown url type: 192.168.99.99     Generate Http Get Traffic   192.168.99.99   1
