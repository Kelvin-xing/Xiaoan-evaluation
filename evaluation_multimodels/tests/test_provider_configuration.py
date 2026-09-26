from xiaoan_eval_core import model_config
from xiaoan_eval_core.llm_adapter import wire_api

def test_provider_matrix_has_requested_models():
    values = {'XIAOAN_CLAUDE_LATEST_MODEL':'claude-sonnet-5','XIAOAN_CLAUDE_SECOND_MODEL':'claude-sonnet-5','XIAOAN_CLAUDE_JUDGE_MODEL':'claude-sonnet-5','XIAOAN_GPT_LATEST_MODEL':'gpt-5.6-luna','XIAOAN_GPT_SECOND_MODEL':'gpt-5.6-luna','XIAOAN_GPT_JUDGE_MODEL':'gpt-5.6-luna','XIAOAN_GEMINI_LATEST_MODEL':'gemini-3.8-flash','XIAOAN_GEMINI_SECOND_MODEL':'gemini-3.1-pro-preview','XIAOAN_GEMINI_JUDGE_MODEL':'gemini-3.8-flash','XIAOAN_DEEPSEEK_LATEST_MODEL':'deepseek-chat','XIAOAN_DEEPSEEK_SECOND_MODEL':'deepseek-chat','XIAOAN_DEEPSEEK_JUDGE_MODEL':'deepseek-chat'}
    assert model_config.PROVIDERS == ('claude','gpt','gemini','deepseek')
    assert wire_api('gpt-5.6-luna', values) == 'responses'
    assert wire_api('claude-sonnet-5', values) == 'messages'
    assert wire_api('gemini-3.8-flash', values) == 'gemini_native'
    assert wire_api('deepseek-chat', values) == 'chat_completions'
    assert model_config.provider_for_model('deepseek-chat', values) == 'deepseek'
