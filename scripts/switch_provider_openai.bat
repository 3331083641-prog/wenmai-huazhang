@echo off
powershell -NoProfile -ExecutionPolicy Bypass -Command "$p='D:\wenmai-huazhang\backend\.env'; $t=[IO.File]::ReadAllText($p,[Text.Encoding]::UTF8); $t=[regex]::Replace($t,'(?m)^GENERATION_PROVIDER=.*$','GENERATION_PROVIDER=openai_image'); [IO.File]::WriteAllText($p,$t,(New-Object Text.UTF8Encoding($false)))"
echo GENERATION_PROVIDER=openai_image