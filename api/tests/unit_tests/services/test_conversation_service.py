import uuid
from unittest.mock import MagicMock, patch

from core.app.entities.app_invoke_entities import InvokeFrom
from services.conversation_service import ConversationService


class TestConversationService:
    def test_pagination_with_empty_include_ids(self):
        """Test that empty include_ids returns empty result"""
        mock_session = MagicMock()
        mock_app_model = MagicMock(id=str(uuid.uuid4()))
        mock_user = MagicMock(id=str(uuid.uuid4()))

        result = ConversationService.pagination_by_last_id(
            session=mock_session,
            app_model=mock_app_model,
            user=mock_user,
            last_id=None,
            limit=20,
            invoke_from=InvokeFrom.WEB_APP,
            include_ids=[],  # Empty include_ids should return empty result
            exclude_ids=None,
        )

        assert result.data == []
        assert result.has_more is False
        assert result.limit == 20

    def test_pagination_with_non_empty_include_ids(self):
        """Test that non-empty include_ids filters properly"""
        mock_session = MagicMock()
        mock_app_model = MagicMock(id=str(uuid.uuid4()))
        mock_user = MagicMock(id=str(uuid.uuid4()))

        # Mock the query results
        mock_conversations = [MagicMock(id=str(uuid.uuid4())) for _ in range(3)]
        mock_session.scalars.return_value.all.return_value = mock_conversations
        mock_session.scalar.return_value = 0

        with patch("services.conversation_service.select") as mock_select:
            mock_stmt = MagicMock()
            mock_select.return_value = mock_stmt
            mock_stmt.where.return_value = mock_stmt
            mock_stmt.order_by.return_value = mock_stmt
            mock_stmt.limit.return_value = mock_stmt
            mock_stmt.subquery.return_value = MagicMock()

            result = ConversationService.pagination_by_last_id(
                session=mock_session,
                app_model=mock_app_model,
                user=mock_user,
                last_id=None,
                limit=20,
                invoke_from=InvokeFrom.WEB_APP,
                include_ids=["conv1", "conv2"],  # Non-empty include_ids
                exclude_ids=None,
            )

            # Verify the where clause was called with id.in_
            assert mock_stmt.where.called

    def test_pagination_with_empty_exclude_ids(self):
        """Test that empty exclude_ids doesn't filter"""
        mock_session = MagicMock()
        mock_app_model = MagicMock(id=str(uuid.uuid4()))
        mock_user = MagicMock(id=str(uuid.uuid4()))

        # Mock the query results
        mock_conversations = [MagicMock(id=str(uuid.uuid4())) for _ in range(5)]
        mock_session.scalars.return_value.all.return_value = mock_conversations
        mock_session.scalar.return_value = 0

        with patch("services.conversation_service.select") as mock_select:
            mock_stmt = MagicMock()
            mock_select.return_value = mock_stmt
            mock_stmt.where.return_value = mock_stmt
            mock_stmt.order_by.return_value = mock_stmt
            mock_stmt.limit.return_value = mock_stmt
            mock_stmt.subquery.return_value = MagicMock()

            result = ConversationService.pagination_by_last_id(
                session=mock_session,
                app_model=mock_app_model,
                user=mock_user,
                last_id=None,
                limit=20,
                invoke_from=InvokeFrom.WEB_APP,
                include_ids=None,
                exclude_ids=[],  # Empty exclude_ids should not filter
            )

            # Result should contain the mocked conversations
            assert len(result.data) == 5

    def test_pagination_with_non_empty_exclude_ids(self):
        """Test that non-empty exclude_ids filters properly"""
        mock_session = MagicMock()
        mock_app_model = MagicMock(id=str(uuid.uuid4()))
        mock_user = MagicMock(id=str(uuid.uuid4()))

        # Mock the query results
        mock_conversations = [MagicMock(id=str(uuid.uuid4())) for _ in range(3)]
        mock_session.scalars.return_value.all.return_value = mock_conversations
        mock_session.scalar.return_value = 0

        with patch("services.conversation_service.select") as mock_select:
            mock_stmt = MagicMock()
            mock_select.return_value = mock_stmt
            mock_stmt.where.return_value = mock_stmt
            mock_stmt.order_by.return_value = mock_stmt
            mock_stmt.limit.return_value = mock_stmt
            mock_stmt.subquery.return_value = MagicMock()

            result = ConversationService.pagination_by_last_id(
                session=mock_session,
                app_model=mock_app_model,
                user=mock_user,
                last_id=None,
                limit=20,
                invoke_from=InvokeFrom.WEB_APP,
                include_ids=None,
                exclude_ids=["conv1", "conv2"],  # Non-empty exclude_ids
            )

            # Verify the where clause was called for exclusion
            assert mock_stmt.where.called

    def test_update_consultation_brief_for_app(self):
        mock_app_model = MagicMock()
        mock_message = MagicMock()
        mock_conversation = MagicMock(first_message=mock_message)

        with patch.object(
            ConversationService, "get_conversation_for_app", return_value=mock_conversation
        ), patch("services.conversation_service.db.session.commit") as mock_commit:
            result = ConversationService.update_consultation_brief_for_app(
                mock_app_model, "conversation-id", "患者描述"
            )

        assert result is mock_conversation
        assert mock_message.consultation_brief == "患者描述"
        mock_commit.assert_called_once()

    def test_search_conversations_keyword_filter(self):
        mock_session = MagicMock()
        mock_app_model = MagicMock(id=str(uuid.uuid4()))

        mock_stmt = MagicMock()
        mock_stmt.where.return_value = mock_stmt
        mock_stmt.order_by.return_value = mock_stmt
        mock_stmt.offset.return_value = mock_stmt
        mock_stmt.limit.return_value = mock_stmt
        mock_stmt.subquery.return_value = MagicMock()

        mock_count_stmt = MagicMock()
        mock_count_stmt.select_from.return_value = mock_count_stmt

        mock_session.scalar.return_value = 0
        mock_session.scalars.return_value.all.return_value = []

        with patch("services.conversation_service.select", side_effect=[mock_stmt, mock_count_stmt]):
            result = ConversationService.search_conversations(
                session=mock_session,
                app_model=mock_app_model,
                page=1,
                limit=10,
                end_user_id=None,
                start_time=None,
                end_time=None,
                keyword="感冒",
                sort_by="-updated_at",
            )

        assert result["page"] == 1
        assert result["limit"] == 10
        assert mock_stmt.where.called
