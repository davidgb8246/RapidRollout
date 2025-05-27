from django.shortcuts import redirect


def root_redirect(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return redirect('login')
