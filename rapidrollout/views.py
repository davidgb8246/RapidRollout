from django.shortcuts import redirect, render


def root_redirect(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return redirect('login')


def custom_404(request, exception):
    return render(request, 'errors/404.html', status=404)
