from api.services.voice_intent import parse_voice_intent


def test_voice_routes_ugc_generation():
    result = parse_voice_intent("Create three UGC ads for Cella Coffee for Instagram")
    assert result.intent == "create_ugc"
    assert result.requires_approval is False
    assert "cella coffee" in result.entity.lower()


def test_voice_routes_scheduling_with_human_gate():
    result = parse_voice_intent("Schedule the approved reel tomorrow at 9 AM")
    assert result.intent == "schedule_content"
    assert result.requires_approval is True


def test_voice_defaults_to_campaign_command():
    result = parse_voice_intent("Launch a seven day campaign for the summer sale")
    assert result.intent == "create_campaign"
