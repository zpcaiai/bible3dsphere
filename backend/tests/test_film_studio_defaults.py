import pytest

from routers.film_studio import (
    DEFAULT_SCENE_COUNT,
    FIRST_CENTURY_ISRAEL_VISUAL_CONTEXT,
    StartReq,
    _historical_video_prompt,
    _split_system_prompt,
    film_studio_page,
)


pytestmark = pytest.mark.no_db


def test_film_studio_defaults_to_three_scenes_in_api_and_page():
    assert DEFAULT_SCENE_COUNT == 3
    assert StartReq(story_text="test storyboard").num_scenes == 3

    page = film_studio_page()
    assert 'id="ns" type="number" value="3" min="1"' in page
    assert "document.getElementById('ns').value||3" in page


def test_every_generation_prompt_gets_first_century_visual_context():
    prompt = _historical_video_prompt("A teacher speaks beside a village well.")

    assert prompt.startswith(FIRST_CENTURY_ISRAEL_VISUAL_CONTEXT)
    assert "first-century Roman Judea and Galilee" in prompt
    assert "linen or wool tunics" in prompt
    assert "limestone or basalt homes" in prompt
    assert "pottery, amphorae, oil lamps" in prompt
    assert "olive and fig trees" in prompt
    assert "No modern, medieval" in prompt


def test_story_splitter_requires_period_details_in_each_scene():
    system_prompt = _split_system_prompt(3)

    assert "produce exactly 3 scene entries" in system_prompt
    assert "Every video_prompt MUST follow this visual bible" in system_prompt
    assert "inside every scene's video_prompt" in system_prompt
