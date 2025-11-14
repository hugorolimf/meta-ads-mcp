import os
import pytest

# Skip this test entirely if the optional 'openai' dependency is not installed
openai = pytest.importorskip("openai", reason="openai package not installed")


@pytest.mark.skipif(
    True,
    reason="Pipeboard integration removed - update this test for your infrastructure"
)
def test_openai_mcp_integration():
    """Test OpenAI integration with Meta Ads MCP.
    
    NOTE: This test was previously configured for Pipeboard service.
    Update the server URL and authentication method for your new infrastructure.
    """
    client = openai.OpenAI()

    resp = client.responses.create(
        model="gpt-4.1",
        tools=[{
            "type": "mcp",
            "server_label": "meta-ads",
            "server_url": "http://localhost:8080",  # Update with your server URL
            "headers": {
                "Authorization": f"Bearer {os.getenv('META_ACCESS_TOKEN')}"
            },
            "require_approval": "never",
        }],
        input="What are my meta ad accounts? Do not pass access_token since auth is already done.",
    )

    assert resp.output_text is not None
    print(resp.output_text)
