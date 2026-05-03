param(
    [ValidateSet('teacher_admin', 'student_public')]
    [string]$Target = 'student_public',
    [ValidateSet('stdout', 'stderr')]
    [string]$Stream = 'stdout',
    [int]$Tail = 80
)

powershell -ExecutionPolicy Bypass -File D:\lesson_app\scripts\devops\Get-MvlDevLogs.ps1 -Target $Target -Stream $Stream -Tail $Tail
