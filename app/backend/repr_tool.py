from langchain.tools.base import BaseTool
import pandas as pd

class MyPythonAstREPLTool(BaseTool):
    name = "python_repl_ast"
    description = (
        "A Python shell. Use this to execute python commands. "
        "Input should be a valid python command. "
        "When using this tool, sometimes output is abbreviated - "
        "make sure it does not look abbreviated before using it in your answer."
    )
    result: pd.DataFrame = pd.DataFrame()
    realtool: BaseTool
    
    def _run(
        self,
        query,
        run_manager=None,
    ) -> str:
        ret = self.realtool._run(query, run_manager)
        if isinstance(ret, pd.Series):
            self.result = ret.to_frame()
        elif isinstance(ret, pd.DataFrame):
            self.result = ret
        return ret
    
    async def _arun(
        self,
        query,
        run_manager = None,
    ) -> str:
        raise NotImplementedError("PythonReplTool does not support async")