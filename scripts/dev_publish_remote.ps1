param(
    [ValidateSet('all', 'teacher', 'student')]
    [string]$Target = 'all',
    [switch]$AutoCommit,
    [string]$Message
)

powershell -ExecutionPolicy Bypass -File D:\lesson_app\scripts\devops\Publish-MvlRemoteDev.ps1 -Target $Target -AutoCommit:$AutoCommit -Message $Message
