from api.services.video_prompt import VideoPromptInput, compile_video_prompt


def test_video_prompt_follows_universal_order():
    prompt = compile_video_prompt(VideoPromptInput(
        idea="A creator unboxes a ceramic coffee dripper in a bright kitchen.",
        camera="handheld close-up that slowly pushes in",
        subject="creator in their late 20s, relaxed and curious",
        environment="sunlit apartment kitchen",
        lighting="soft natural morning light",
        style="realistic commercial",
        motion="calm, natural hand movement",
        dialogue="I finally found a dripper that doesn't make mornings complicated.",
    ))
    labels = ["SCENE:", "CAMERA:", "SUBJECT:", "ENVIRONMENT:", "LIGHTING & STYLE:", "MOTION:", "DIALOGUE:"]
    positions = [prompt.index(label) for label in labels]
    assert positions == sorted(positions)
    assert "ceramic coffee dripper" in prompt


def test_video_prompt_rejects_conflicting_styles():
    prompt = compile_video_prompt(VideoPromptInput(
        idea="Product demo",
        style="cinematic, anime, documentary",
    ))
    assert "cinematic" in prompt
    assert "anime" not in prompt
