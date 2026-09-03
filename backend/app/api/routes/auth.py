"""Authentication endpoints: registration, session lifecycle, and recovery.

Every route below is the only place that ever reads or writes a request's
identity: it either sets/clears the two auth cookies, or delegates to
``AuthService``, never both to a database directly. Error responses use the
same ``{"code", "message"}`` envelope the rest of the API already uses.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.api.dependencies import (
    CSRF_COOKIE_NAME,
    SESSION_COOKIE_NAME,
    get_current_session,
    get_current_user,
    require_csrf,
)
from app.api.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    ResetPasswordRequest,
    UserResponse,
    VerifyEmailConfirmRequest,
)
from app.composition import get_auth_service, get_settings
from app.config import Settings
from app.identity.contracts import Session, User
from app.identity.rate_limit import RateLimitExceededError, enforce_rate_limit
from app.identity.service import (
    AccountDisabledError,
    AuthService,
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    TokenInvalidError,
    WeakPasswordError,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id, email=user.email, display_name=user.display_name, is_active=user.is_active,
        email_verified=user.email_verified, created_at=user.created_at, updated_at=user.updated_at,
        last_login_at=user.last_login_at,
    )


def _rate_limited(error: RateLimitExceededError) -> HTTPException:
    return HTTPException(
        status_code=429,
        detail={"code": "rate_limited", "message": "Too many attempts. Try again shortly."},
        headers={"Retry-After": str(int(error.retry_after_seconds) + 1)},
    )


def _set_auth_cookies(response: Response, *, settings: Settings, session_token: str, csrf_token: str, max_age: int) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME, value=session_token, httponly=True,
        secure=settings.effective_cookie_secure, samesite="lax", path="/", max_age=max_age,
    )
    # Deliberately readable by JS: the CSRF cookie's whole purpose is for the
    # frontend to copy its value into the X-CSRF-Token header. It carries no
    # authority on its own -- only the paired session cookie does.
    response.set_cookie(
        key=CSRF_COOKIE_NAME, value=csrf_token, httponly=False,
        secure=settings.effective_cookie_secure, samesite="lax", path="/", max_age=max_age,
    )


def _clear_auth_cookies(response: Response, *, settings: Settings) -> None:
    response.delete_cookie(
        SESSION_COOKIE_NAME, path="/", secure=settings.effective_cookie_secure, httponly=True, samesite="lax",
    )
    response.delete_cookie(
        CSRF_COOKIE_NAME, path="/", secure=settings.effective_cookie_secure, httponly=False, samesite="lax",
    )


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(
    request: RegisterRequest, http_request: Request, service: AuthService = Depends(get_auth_service),
) -> UserResponse:
    try:
        await enforce_rate_limit(service.rate_limiter, "register", _client_ip(http_request))
    except RateLimitExceededError as error:
        raise _rate_limited(error) from error
    try:
        user = await service.register(email=request.email, password=request.password, display_name=request.display_name)
    except EmailAlreadyRegisteredError as error:
        raise HTTPException(
            status_code=409,
            detail={"code": "email_already_registered", "message": "An account with that email already exists."},
        ) from error
    except WeakPasswordError as error:
        raise HTTPException(status_code=422, detail={"code": "weak_password", "message": str(error)}) from error
    return _user_response(user)


@router.post("/login", response_model=UserResponse)
async def login(
    request: LoginRequest, http_request: Request, response: Response,
    service: AuthService = Depends(get_auth_service), settings: Settings = Depends(get_settings),
) -> UserResponse:
    try:
        await enforce_rate_limit(service.rate_limiter, "login", _client_ip(http_request), request.email)
    except RateLimitExceededError as error:
        raise _rate_limited(error) from error
    try:
        user, session_token, csrf_token = await service.login(
            email=request.email, password=request.password,
            user_agent=http_request.headers.get("user-agent"), ip_address=_client_ip(http_request),
        )
    except InvalidCredentialsError as error:
        raise HTTPException(
            status_code=401, detail={"code": "invalid_credentials", "message": "Invalid email or password."},
        ) from error
    except AccountDisabledError as error:
        raise HTTPException(
            status_code=403, detail={"code": "account_disabled", "message": "This account has been disabled."},
        ) from error
    _set_auth_cookies(
        response, settings=settings, session_token=session_token, csrf_token=csrf_token,
        max_age=service.session_absolute_ttl_seconds,
    )
    return _user_response(user)


@router.post("/logout", response_model=MessageResponse, dependencies=[Depends(require_csrf)])
async def logout(
    response: Response, session: Session = Depends(get_current_session),
    service: AuthService = Depends(get_auth_service), settings: Settings = Depends(get_settings),
) -> MessageResponse:
    await service.logout(session_id=session.id)
    _clear_auth_cookies(response, settings=settings)
    return MessageResponse(message="Signed out.")


@router.post("/logout-all", response_model=MessageResponse, dependencies=[Depends(require_csrf)])
async def logout_all(
    response: Response, user: User = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service), settings: Settings = Depends(get_settings),
) -> MessageResponse:
    count = await service.logout_all(user_id=user.id)
    _clear_auth_cookies(response, settings=settings)
    return MessageResponse(message=f"Signed out of {count} session(s).")


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)) -> UserResponse:
    return _user_response(user)


@router.post("/change-password", response_model=MessageResponse, dependencies=[Depends(require_csrf)])
async def change_password(
    request: ChangePasswordRequest, http_request: Request, user: User = Depends(get_current_user),
    session: Session = Depends(get_current_session), service: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    try:
        await enforce_rate_limit(service.rate_limiter, "change_password", _client_ip(http_request), str(user.id))
    except RateLimitExceededError as error:
        raise _rate_limited(error) from error
    try:
        await service.change_password(
            user_id=user.id, current_password=request.current_password,
            new_password=request.new_password, keep_session_id=session.id,
        )
    except InvalidCredentialsError as error:
        raise HTTPException(
            status_code=401, detail={"code": "invalid_credentials", "message": "Current password is incorrect."},
        ) from error
    except WeakPasswordError as error:
        raise HTTPException(status_code=422, detail={"code": "weak_password", "message": str(error)}) from error
    return MessageResponse(message="Password changed. Other sessions have been signed out.")


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    request: ForgotPasswordRequest, http_request: Request, service: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    """Always returns the same message, whether or not the address is registered."""

    try:
        await enforce_rate_limit(service.rate_limiter, "forgot_password", _client_ip(http_request), request.email)
    except RateLimitExceededError as error:
        raise _rate_limited(error) from error
    await service.forgot_password(email=request.email)
    return MessageResponse(message="If an account exists for that email, we've sent instructions.")


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    request: ResetPasswordRequest, http_request: Request, service: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    try:
        await enforce_rate_limit(service.rate_limiter, "reset_password", _client_ip(http_request))
    except RateLimitExceededError as error:
        raise _rate_limited(error) from error
    try:
        await service.reset_password(token=request.token, new_password=request.new_password)
    except TokenInvalidError as error:
        raise HTTPException(
            status_code=400, detail={"code": "invalid_token", "message": "This link is invalid or has expired."},
        ) from error
    except WeakPasswordError as error:
        raise HTTPException(status_code=422, detail={"code": "weak_password", "message": str(error)}) from error
    return MessageResponse(message="Password reset. Sign in with your new password.")


@router.post("/verify-email/resend", response_model=MessageResponse, dependencies=[Depends(require_csrf)])
async def resend_verification(
    http_request: Request, user: User = Depends(get_current_user), service: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    try:
        await enforce_rate_limit(service.rate_limiter, "verify_resend", _client_ip(http_request), str(user.id))
    except RateLimitExceededError as error:
        raise _rate_limited(error) from error
    sent = await service.resend_email_verification(user=user)
    return MessageResponse(message="Verification email sent." if sent else "Your email is already verified.")


@router.post("/verify-email/confirm", response_model=MessageResponse)
async def confirm_verification(
    request: VerifyEmailConfirmRequest, http_request: Request, service: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    try:
        await enforce_rate_limit(service.rate_limiter, "verify_confirm", _client_ip(http_request))
    except RateLimitExceededError as error:
        raise _rate_limited(error) from error
    try:
        await service.confirm_email_verification(token=request.token)
    except TokenInvalidError as error:
        raise HTTPException(
            status_code=400, detail={"code": "invalid_token", "message": "This link is invalid or has expired."},
        ) from error
    return MessageResponse(message="Email verified.")
