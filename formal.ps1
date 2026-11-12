param([Parameter(ValueFromRemainingArguments=$true)][string[]]$FormalArguments)
& python (Join-Path $PSScriptRoot 'run.py') @FormalArguments
exit $LASTEXITCODE
