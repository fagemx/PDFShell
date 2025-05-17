# tests/test_agent.py
import pytest
import importlib # 確保 importlib 已導入
from unittest.mock import patch, MagicMock
from langchain.agents import AgentType # <--- 新增導入

def test_nl_execute_basic_flow(caplog):
    """
    Tests the basic flow of nl_execute, ensuring critical dependencies are mocked
    before the agent module is imported/reloaded.
    """
    with patch('tools.loader.load_tools', return_value=[]) as mock_load_tools, \
         patch('langchain_openai.ChatOpenAI', autospec=True) as mock_chat_openai_class, \
         patch('langchain.agents.initialize_agent') as mock_initialize_agent_in_langchain:

        # ✨ 提前決定 initialize_agent 要回傳的物件
        mock_agent_executor_instance = MagicMock()
        mock_initialize_agent_in_langchain.return_value = mock_agent_executor_instance

        # 這時再 import，agent_module.agent 就會綁到 mock_agent_executor_instance
        if 'agent.agent' in locals() or 'agent.agent' in globals() or 'agent_module' in locals() or 'agent_module' in globals():
            import agent.agent as agent_module_for_reload # type: ignore
            importlib.reload(agent_module_for_reload)
            agent_module = agent_module_for_reload
        else:
            import agent.agent as agent_module # type: ignore
        
        # mock_load_tools is already configured with return_value=[]
        mock_llm_instance = mock_chat_openai_class.return_value # Instance from the ChatOpenAI class mock
        
        expected_output_path = "/path/to/mocked/output.pdf"
        # 設定 mock_agent_executor_instance (即 agent_module.agent 的 mock) 的 run 方法的返回值
        mock_agent_executor_instance.run.return_value = expected_output_path

        user_query = "Merge fileA.pdf and fileB.pdf into merged.pdf"
        actual_output = agent_module.nl_execute(user_query)

        # Assertions
        mock_load_tools.assert_called_once()
        mock_chat_openai_class.assert_called_once_with(model="gpt-4o-mini", temperature=0)
        mock_initialize_agent_in_langchain.assert_called_once_with(
            tools=[],
            llm=mock_llm_instance,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
            handle_parsing_errors=True,
        )
        # 現在我們驗證的是 mock_agent_executor_instance 的 run 方法
        mock_agent_executor_instance.run.assert_called_once_with(user_query)
        assert actual_output == expected_output_path

    # Optional: Check for log messages if verbose=True was expected to produce them via caplog
    # import logging
    # caplog.set_level(logging.INFO) # Ensure caplog captures INFO level
    # ... (re-run or structure test to capture logs appropriately) ...
    # if agent_module.agent.verbose: # Or based on how verbose is set for the test
    #     assert "some expected log message" in caplog.text

# 注意: 
# 1. 上述測試假設 `agent.agent.agent` 指的是在 `agent.agent` 模塊中名為 `agent` 的 Langchain Agent 實例。
# 2. `mock_load_tools_in_module` 參數雖然在函數簽名中，但由於我們用 `MagicMock(return_value=[])` 直接替換了 `load_tools`，
#    所以我們主要關心它的副作用 (即 `TOOLS` 在 `agent.py` 中變為 `[]`)，而不是直接使用這個 mock 對象。
#    如果需要斷言 `load_tools` 被調用，可以不直接替換為 MagicMock 實例，而是傳入一個 MagicMock 對象，然後對其進行斷言。
#    例如 `@patch('agent.agent.load_tools')` 然後 `mock_load_tools_in_module.return_value = []`。
#    但對於此測試，使其返回空列表就足夠了。

# (可選) 更完整的集成測試 (需要真實 API Key 和環境配置):
# def test_nl_execute_integration_example(tmp_path):
#     # from agent.agent import nl_execute # 移到函數內部確保環境已準備好
#     # import os
#     # if not os.getenv("OPENAI_API_KEY"):
#     #     pytest.skip("OPENAI_API_KEY not set, skipping integration test.")
#     
#     # # 準備測試用的 dummy tool (如果需要)
#     # # 例如，在 tests/fixtures/tools/dummy_tool.yml 和 .py
#     # # ... (創建 dummy tool yml 和 py) ...
#     
#     # # 假設有一個 dummy_tool.py 可以創建一個文件
#     # query = "run dummy_tool to create a file in output_dir"
#     # expected_file_name = "dummy_output.txt"
#     # # 執行 nl_execute，它應該調用 dummy_tool
#     # # 這裡的 nl_execute 應該是未經修補的，或者只修補 LLM 以獲得可預測的工具調用
#     # # result = nl_execute(query) 
#     # # assert expected_file_name in result
#     # # assert (tmp_path / expected_file_name).exists()
#     pass 