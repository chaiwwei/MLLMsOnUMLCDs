@echo off
setlocal enabledelayedexpansion

:: Define the list of models
set "models=QWen GPT Gemini Mistral Grok Claude"

:: Outer loop: numbers from 1 to 15 (padded to 3 digits)
for /L %%n in (3,1,15) do (
    :: Pad number with leading zeros to make it 3 digits
    set "num=000%%n"
    set "num=!num:~-3!"
    
    :: Inner loop: iterate through each model
    for %%m in (%models%) do (
        echo Running: python mainv2.0.py -g !num!-GroundTruth.json -p !num!-Pred-%%m.json -o !num!-Result-%%m.json
        python mainv2.0.py -g !num!-GroundTruth.json -p !num!-Pred-%%m.json -o !num!-Result-%%m.json
    )
)

echo All iterations completed.
pause