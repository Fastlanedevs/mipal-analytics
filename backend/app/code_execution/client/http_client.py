from typing import Dict, Any, Optional
from uuid import UUID
from app.code_execution.api.dto import CodeExecutionRequestDTO, CodeExecutionResponseDTO, CodeExecutionResultDTO, \
    CodeExecutionStatusDTO
import requests
from pkg.auth_token_client.client import TokenClient, TokenPayload
import pandas as pd
import numpy as np
import json
from io import StringIO
import re


class CodeExecutionClient:
    def __init__(self, base_url: str, token_client: TokenClient):
        self.base_url: str = base_url

        self.token_client: TokenClient = token_client

    def _clean_input_data(self, input_data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Clean input data to handle non-JSON-compliant values."""
        if not input_data:
            return input_data

        cleaned_data = input_data.copy()
        if 'df' in cleaned_data:
            cleaned_df = []
            for row in cleaned_data['df']:
                cleaned_row = {}
                for key, value in row.items():
                    if isinstance(value, float):
                        if pd.isna(value) or np.isinf(value):
                            cleaned_row[key] = None
                        else:
                            cleaned_row[key] = value
                    else:
                        cleaned_row[key] = value
                cleaned_df.append(cleaned_row)
            cleaned_data['df'] = cleaned_df
        return cleaned_data

    def _get_headers(self, user_id: str) -> Dict[str, str]:
        """
        Get headers for API requests.
        
        Args:
            user_id: User ID for token generation
            
        Returns:
            Dict[str, str]: Headers dictionary
        """
        payload = TokenPayload(user_id=user_id, joined_org=False, role="")
        tokens = self.token_client.create_tokens(payload)
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {tokens['access_token']}"
        }

    def _make_request(
            self,
            method: str,
            endpoint: str,
            data: Dict[str, Any],
            headers: Dict[str, str],
            timeout: int = 35
    ) -> Dict[str, Any]:
        """
        Make an HTTP request to the code execution service.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            data: Request data
            headers: Request headers
            timeout: Request timeout in seconds
            
        Returns:
            Dict[str, Any]: Response data
            
        Raises:
            requests.exceptions.RequestException: If the request fails
        """
        try:
            response = requests.request(
                method=method,
                url=f"{self.base_url}{endpoint}",
                json=data,
                headers=headers,
                timeout=timeout
            )

            print(f"Response: {response.json()}")  

            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
           print(f"Request failed: {str(e)}")
           raise

    def execute_code_sync(
            self,
            user_id: str,
            code: str,
            input_data: Optional[Dict[str, Any]] = None,
            timeout_seconds: int = 30
    ) -> CodeExecutionResultDTO:
        """
        Execute code synchronously.
        
        Args:
            user_id: User ID
            code: Python code to execute
            input_data: Optional input data
            timeout_seconds: Maximum execution time in seconds
            
        Returns:
            CodeExecutionResultDTO: Execution result
        """
        try:
            # Clean and convert input data to ensure JSON serializability
            cleaned_input_data = self._clean_input_data(input_data)

            # Add DataFrame handling code if input data contains a DataFrame
            if 'df' in cleaned_input_data:
                # Add code to convert the input data to DataFrame and assign to df
                df_code = """
if 'df' in input_data:
    df = pd.DataFrame(input_data['df'])
"""
                code = df_code + code

            # Construct request
            request = CodeExecutionRequestDTO(
                code=code,
                input_data=cleaned_input_data,
                timeout_seconds=timeout_seconds
            )

            # Make API call
            response = self._make_request(
                method="POST",
                endpoint="/execute/ml_run",
                data=request.model_dump(),
                headers=self._get_headers(user_id)
            )

            # Parse response
            result = CodeExecutionResultDTO.model_validate(response)
            
            # Convert stdout to DataFrame 
            df_parsed = pd.read_csv(StringIO(result.stdout))
            result.dataframe = df_parsed

            return result

        except requests.exceptions.HTTPError as e:
            error_detail = None
            try:
                error_detail = e.response.json().get('detail')
            except:
                error_detail = str(e)
            raise Exception(f"Code execution failed: {error_detail}")
        except Exception as e:
            print(f"Error executing code: {str(e)}")
            raise

    def execute_code_async(self, code: str, input_data: Optional[Dict[str, Any]] = None) -> CodeExecutionResponseDTO:
        request_data = CodeExecutionRequestDTO(
            code=code,
            input_data=input_data
        ).model_dump()

        response = requests.post(
            f"{self.base_url}/execute/async",
            json=request_data,
            headers=self.headers
        )

        response.raise_for_status()
        return CodeExecutionResponseDTO(**response.json())

    def get_execution_status(self, execution_id: UUID) -> CodeExecutionStatusDTO:
        response = requests.get(
            f"{self.base_url}/execute/{execution_id}",
            headers=self.headers
        )

        response.raise_for_status()
        return CodeExecutionStatusDTO(**response.json())

    def get_execution_result(self, execution_id: UUID) -> CodeExecutionResultDTO:
        response = requests.get(
            f"{self.base_url}/execute/{execution_id}/result",
            headers=self.headers
        )

        response.raise_for_status()
        return CodeExecutionResultDTO(**response.json())

    def cancel_execution(self, execution_id: UUID) -> CodeExecutionResponseDTO:
        response = requests.delete(
            f"{self.base_url}/execute/{execution_id}",
            headers=self.headers
        )

        response.raise_for_status()
        return CodeExecutionResponseDTO(**response.json())


if __name__ == "__main__":
    client = CodeExecutionClient("https://code-execution.mipal.ai")
    # Generate and set token
    client.generate_token_from_user_id("user123")
    # Execute code
    print(client.execute_code_sync("print('Hello, World!')"))
