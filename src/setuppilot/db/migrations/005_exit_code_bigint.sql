-- Allow exit codes larger than 32-bit signed integer (e.g. Windows DWORD exit codes
-- and HRESULTs from winget such as 0x8A15002B = 2316632107).
alter table steps alter column exit_code type bigint;
