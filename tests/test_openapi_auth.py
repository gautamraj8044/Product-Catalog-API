from app.main import app


def test_openapi_security_scheme_matches_protected_operations():
    app.openapi_schema = None
    schema = app.openapi()

    security_schemes = schema["components"]["securitySchemes"]
    assert "BearerAuth" in security_schemes
    assert security_schemes["BearerAuth"]["type"] == "http"
    assert security_schemes["BearerAuth"]["scheme"] == "bearer"

    protected_operation = schema["paths"]["/api/v1/products"]["get"]
    assert protected_operation["security"] == [{"BearerAuth": []}]

    login_operation = schema["paths"]["/api/v1/auth/login"]["post"]
    assert "security" not in login_operation
