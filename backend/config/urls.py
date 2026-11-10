from django.urls import include, path

urlpatterns = [
    path("api/", include("routing.api.urls")),
]

handler400 = "routing.api.errors.bad_request"
handler404 = "routing.api.errors.not_found"
handler500 = "routing.api.errors.server_error"
