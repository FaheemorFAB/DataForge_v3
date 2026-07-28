import unittest
from unittest.mock import MagicMock, patch

# Mock get_supabase_client during import to prevent real connections
with patch('dataforge.db.get_supabase_client') as mock_get:
    mock_get.return_value = MagicMock()
    from dataforge import db

class TestDBRobustness(unittest.TestCase):
    def test_db_insert_empty_data(self):
        mock_res = MagicMock()
        mock_res.data = []  # Empty list returned (e.g. RLS policy blocked insert)
        
        mock_table = MagicMock()
        mock_table.insert.return_value.execute.return_value = mock_res
        
        db.db_client = MagicMock()
        db.db_client.table.return_value = mock_table
        
        result = db.db_insert("uploads", {"filename": "test.csv"})
        self.assertEqual(result, {})

    def test_db_update_empty_data(self):
        mock_res = MagicMock()
        mock_res.data = []  # Empty list returned (e.g. no record matched ID on update)
        
        mock_table = MagicMock()
        mock_table.update.return_value.eq.return_value.execute.return_value = mock_res
        
        db.db_client = MagicMock()
        db.db_client.table.return_value = mock_table
        
        result = db.db_update("uploads", 999, {"filename": "new.csv"})
        self.assertEqual(result, {})

if __name__ == '__main__':
    unittest.main()
