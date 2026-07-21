from app.routers.echo_conversation import _casual_response


def test_casual_conversation_is_not_forced_through_memory_retrieval():
    greeting = _casual_response("hieee")
    assert greeting is not None
    assert greeting.startswith("Hii!")
    assert _casual_response("am building a project") == "That sounds exciting. Tell me more about what you're building."


def test_memory_questions_continue_to_retrieval():
    assert _casual_response("What project am I building?") is None
