"""Unit tests for the python_template_server.models module."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from python_template_server.models import (
    BaseResponse,
    CertificateConfigModel,
    CORSConfigModel,
    CustomJSONResponse,
    DatabaseConfig,
    GetHealthResponse,
    GetLoginResponse,
    JSONResponseConfigModel,
    RateLimitConfigModel,
    ResponseCode,
    SecurityConfigModel,
    TemplateServerConfig,
)


# Template Server Configuration Models
class TestSecurityConfigModel:
    """Unit tests for the SecurityConfigModel class."""

    def test_model_dump(self, mock_security_config_dict: dict, mock_security_config: SecurityConfigModel) -> None:
        """Test the model_dump method."""
        assert mock_security_config.model_dump() == mock_security_config_dict


class TestCORSConfigModel:
    """Unit tests for the CORSConfigModel class."""

    def test_model_dump(self, mock_cors_config_dict: dict, mock_cors_config: CORSConfigModel) -> None:
        """Test the model_dump method."""
        assert mock_cors_config.model_dump() == mock_cors_config_dict


class TestRateLimitConfigModel:
    """Unit tests for the RateLimitConfigModel class."""

    def test_model_dump(self, mock_rate_limit_config_dict: dict, mock_rate_limit_config: RateLimitConfigModel) -> None:
        """Test the model_dump method."""
        assert mock_rate_limit_config.model_dump() == mock_rate_limit_config_dict


class TestCertificateConfigModel:
    """Unit tests for the CertificateConfigModel class."""

    def test_model_dump(
        self, mock_certificate_config_dict: dict, mock_certificate_config: CertificateConfigModel
    ) -> None:
        """Test the model_dump method."""
        assert mock_certificate_config.model_dump() == mock_certificate_config_dict

    def test_ssl_key_file_path_property(self, mock_certificate_config: CertificateConfigModel) -> None:
        """Test the ssl_key_file_path property."""
        assert mock_certificate_config.ssl_key_file_path == Path("/path/to/certs/key.pem")

    def test_ssl_cert_file_path_property(self, mock_certificate_config: CertificateConfigModel) -> None:
        """Test the ssl_cert_file_path property."""
        assert mock_certificate_config.ssl_cert_file_path == Path("/path/to/certs/cert.pem")

    def test_days_valid_field(
        self, mock_certificate_config_dict: dict, mock_certificate_config: CertificateConfigModel
    ) -> None:
        """Test the days_valid field."""
        invalid_config_data = mock_certificate_config_dict.copy()
        invalid_config_data["days_valid"] = -10  # Invalid value

        with pytest.raises(ValidationError):
            CertificateConfigModel(**invalid_config_data)


class TestJSONResponseConfigModel:
    """Unit tests for the JSONResponseConfigModel class."""

    def test_model_dump(
        self, mock_json_response_config_dict: dict, mock_json_response_config: JSONResponseConfigModel
    ) -> None:
        """Test the model_dump method."""
        assert mock_json_response_config.model_dump() == mock_json_response_config_dict


class TestDatabaseConfig:
    """Unit tests for the DatabaseConfig class."""

    def test_model_dump(self, mock_db_config_dict: dict, mock_db_config: DatabaseConfig) -> None:
        """Test the model_dump method."""
        assert mock_db_config.model_dump() == mock_db_config_dict

    def test_db_url_method(self, mock_db_config: DatabaseConfig) -> None:
        """Test the db_url method."""
        filename = "test.db"
        expected_url = f"sqlite:///{mock_db_config.db_directory}/{filename}"
        assert mock_db_config.db_url(filename) == expected_url


class TestTemplateServerConfig:
    """Unit tests for the TemplateServerConfig class."""

    def test_model_dump(
        self,
        mock_template_server_config: TemplateServerConfig,
        mock_security_config_dict: dict,
        mock_cors_config_dict: dict,
        mock_rate_limit_config_dict: dict,
        mock_certificate_config_dict: dict,
        mock_json_response_config_dict: dict,
    ) -> None:
        """Test the model_dump method."""
        expected_dict = {
            "security": mock_security_config_dict,
            "cors": mock_cors_config_dict,
            "rate_limit": mock_rate_limit_config_dict,
            "certificate": mock_certificate_config_dict,
            "json_response": mock_json_response_config_dict,
        }
        assert mock_template_server_config.model_dump() == expected_dict

    def test_save_to_file(
        self,
        tmp_path: Path,
        mock_template_server_config: TemplateServerConfig,
    ) -> None:
        """Test the save_to_file method."""
        config_file = tmp_path / "config.json"
        mock_template_server_config.save_to_file(config_file)
        assert config_file.read_text(encoding="utf-8") == mock_template_server_config.model_dump_json(indent=2) + "\n"


# API Response Models
class TestCustomJSONResponse:
    """Unit tests for the CustomJSONResponse class."""

    def test_configure_method(self, mock_json_response_config: JSONResponseConfigModel) -> None:
        """Test the configure class method."""
        CustomJSONResponse.configure(mock_json_response_config)

        assert CustomJSONResponse._ensure_ascii == mock_json_response_config.ensure_ascii
        assert CustomJSONResponse._allow_nan == mock_json_response_config.allow_nan
        assert CustomJSONResponse._indent == mock_json_response_config.indent
        assert CustomJSONResponse.media_type == mock_json_response_config.media_type

    def test_render_with_unicode(self, mock_json_response_config: JSONResponseConfigModel) -> None:
        """Test rendering JSON with Unicode characters (emojis)."""
        CustomJSONResponse.configure(mock_json_response_config)
        response = CustomJSONResponse(content={"message": "Hello 👋 World 🌍"})

        rendered = response.render({"message": "Hello 👋 World 🌍"})
        assert b"Hello \\ud83d\\udc4b World" not in rendered  # Should NOT be escaped
        assert "👋".encode() in rendered  # Should preserve emoji
        assert "🌍".encode() in rendered

    def test_render_with_ensure_ascii_true(self) -> None:
        """Test rendering with ensure_ascii=True."""
        config = JSONResponseConfigModel(ensure_ascii=True)
        CustomJSONResponse.configure(config)
        response = CustomJSONResponse(content={"message": "Hello 👋"})

        rendered = response.render({"message": "Hello 👋"})
        # With ensure_ascii=True, Unicode should be escaped
        assert b"\\ud83d\\udc4b" in rendered or b"\\u" in rendered

    def test_render_with_indent(self) -> None:
        """Test rendering with indentation."""
        config = JSONResponseConfigModel(indent=2)
        CustomJSONResponse.configure(config)
        response = CustomJSONResponse(content={"key": "value"})

        rendered = response.render({"key": "value"})
        # With indent, output should have newlines and spaces
        assert b"\n" in rendered
        assert b"  " in rendered

    def test_render_compact(self, mock_json_response_config: JSONResponseConfigModel) -> None:
        """Test rendering in compact mode (no indent)."""
        CustomJSONResponse.configure(mock_json_response_config)
        response = CustomJSONResponse(content={"key": "value", "number": 42})

        rendered = response.render({"key": "value", "number": 42})
        # Compact mode should use "," separator without spaces after
        assert rendered == b'{"key":"value","number":42}'


class TestResponseCode:
    """Unit tests for the ResponseCode enum."""

    @pytest.mark.parametrize(
        ("response_code", "status_code"),
        [
            (ResponseCode.OK, 200),
            (ResponseCode.CREATED, 201),
            (ResponseCode.ACCEPTED, 202),
            (ResponseCode.NO_CONTENT, 204),
            (ResponseCode.BAD_REQUEST, 400),
            (ResponseCode.UNAUTHORIZED, 401),
            (ResponseCode.FORBIDDEN, 403),
            (ResponseCode.NOT_FOUND, 404),
            (ResponseCode.CONFLICT, 409),
            (ResponseCode.INTERNAL_SERVER_ERROR, 500),
            (ResponseCode.SERVICE_UNAVAILABLE, 503),
        ],
    )
    def test_enum_values(self, response_code: ResponseCode, status_code: int) -> None:
        """Test the enum values."""
        assert response_code.value == status_code


class TestBaseResponse:
    """Unit tests for the BaseResponse class."""

    def test_model_dump(self) -> None:
        """Test the model_dump method."""
        timestamp = BaseResponse.current_timestamp()
        config_dict: dict = {"message": "Success", "timestamp": timestamp}
        response = BaseResponse(**config_dict)
        assert response.model_dump() == config_dict

    def test_current_timestamp_format(self) -> None:
        """Test the format of the current timestamp."""
        timestamp = BaseResponse.current_timestamp()
        assert timestamp.endswith("Z")
        assert "T" in timestamp


class TestGetHealthResponse:
    """Unit tests for the GetHealthResponse class."""

    def test_model_dump(self) -> None:
        """Test the model_dump method."""
        timestamp = GetHealthResponse.current_timestamp()
        config_dict: dict = {
            "message": "Server is healthy",
            "timestamp": timestamp,
        }
        response = GetHealthResponse(**config_dict)
        assert response.model_dump() == config_dict


class TestGetLoginResponse:
    """Unit tests for the GetLoginResponse class."""

    def test_model_dump(self) -> None:
        """Test the model_dump method."""
        timestamp = GetLoginResponse.current_timestamp()
        config_dict: dict = {
            "message": "Login successful",
            "timestamp": timestamp,
        }
        response = GetLoginResponse(**config_dict)
        assert response.model_dump() == config_dict
