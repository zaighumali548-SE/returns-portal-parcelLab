from django.urls import path

from portal import views

urlpatterns = [
    path("", views.LookupView.as_view(), name="lookup"),
    path(
        "<str:order_number>/articles/",
        views.ArticlesView.as_view(),
        name="articles",
    ),
    path(
        "<str:order_number>/confirm/",
        views.ReturnConfirmationView.as_view(),
        name="return-confirmation",
    ),
    path(
        "<str:order_number>/submit/",
        views.ReturnSubmitView.as_view(),
        name="return-submit",
    ),
    path(
        "<str:order_number>/success/",
        views.ReturnSuccessView.as_view(),
        name="return-success",
    ),
]
