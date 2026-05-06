"""
Tests for core.vector_memory — ChromaDB-backed semantic memory.

ChromaDB is installed, but we mock the client so tests are hermetic.
"""

from unittest.mock import MagicMock, patch

import pytest

from core.vector_memory import VectorMemory

# ─── Fixtures ──────────────────────────────────────────────────────


@pytest.fixture
def mock_collection():
    """A mock ChromaDB collection."""
    coll = MagicMock(name="collection")
    coll.add.return_value = None
    coll.query.return_value = {"documents": [[]], "metadatas": [[]], "distances": [[]]}
    coll.get.return_value = {"ids": [], "metadatas": []}
    coll.count.return_value = 0
    coll.delete.return_value = None
    return coll


@pytest.fixture
def vm(mock_collection):
    """VectorMemory instance with mocked ChromaDB client."""
    mock_client = MagicMock(name="client")
    mock_client.get_or_create_collection.return_value = mock_collection
    with patch("chromadb.PersistentClient", return_value=mock_client), patch("chromadb.config.Settings"):
        yield VectorMemory(), mock_client, mock_collection


# ─── Initialisation ────────────────────────────────────────────────


class TestInit:
    """VectorMemory creates four collections on init."""

    def test_creates_four_collections(self, vm):
        _instance, mock_client, _mock_coll = vm
        assert mock_client.get_or_create_collection.call_count == 4
        names = [call[1]["name"] for call in mock_client.get_or_create_collection.call_args_list]
        assert "conversations" in names
        assert "knowledge" in names
        assert "preferences" in names
        assert "context_saver" in names


# ─── ID generation ─────────────────────────────────────────────────


class TestGenerateId:
    def test_format(self):
        """_generate_id returns a string with prefix_timestamp_hash"""
        vm = VectorMemory.__new__(VectorMemory)
        doc_id = vm._generate_id("hello world", "conv")
        assert doc_id.startswith("conv_")
        parts = doc_id.rsplit("_", 2)
        assert len(parts) == 3  # prefix_YYYYMMDDHHMMSS_hash
        assert len(parts[1]) == 14  # timestamp YYYYMMDDHHMMSS
        assert len(parts[2]) == 12  # MD5 prefix

    def test_different_texts_different_ids(self):
        vm = VectorMemory.__new__(VectorMemory)
        id1 = vm._generate_id("text a", "pref")
        id2 = vm._generate_id("text b", "pref")
        assert id1 != id2


# ─── add_conversation ──────────────────────────────────────────────


class TestAddConversation:
    @pytest.mark.asyncio
    async def test_add_conversation_calls_collection_add(self, vm):
        instance, _client, mock_coll = vm
        doc_id = await instance.add_conversation("Hello", "sess-1", "user")
        assert doc_id != ""
        assert doc_id.startswith("conv_")
        mock_coll.add.assert_called_once()
        _args, kwargs = mock_coll.add.call_args
        assert kwargs["ids"] == [doc_id]
        assert kwargs["documents"] == ["Hello"]
        assert kwargs["metadatas"][0]["session_id"] == "sess-1"
        assert kwargs["metadatas"][0]["role"] == "user"

    @pytest.mark.asyncio
    async def test_add_conversation_exception_returns_empty(self, vm):
        instance, _client, mock_coll = vm
        mock_coll.add.side_effect = ValueError("fail")
        doc_id = await instance.add_conversation("Hi", "s-1", "user")
        assert doc_id == ""


# ─── add_knowledge ─────────────────────────────────────────────────


class TestAddKnowledge:
    @pytest.mark.asyncio
    async def test_add_knowledge(self, vm):
        instance, _client, mock_coll = vm
        doc_id = await instance.add_knowledge("Python is fun", "programming", "docs")
        assert doc_id.startswith("know_")
        mock_coll.add.assert_called_once()
        _args, kwargs = mock_coll.add.call_args
        assert kwargs["documents"] == ["Python is fun"]
        assert kwargs["metadatas"][0]["topic"] == "programming"
        assert kwargs["metadatas"][0]["source"] == "docs"

    @pytest.mark.asyncio
    async def test_add_knowledge_default_source(self, vm):
        instance, _client, _mock_coll = vm
        doc_id = await instance.add_knowledge("X", "topic")
        assert doc_id.startswith("know_")


# ─── add_preference ────────────────────────────────────────────────


class TestAddPreference:
    @pytest.mark.asyncio
    async def test_add_preference(self, vm):
        instance, _client, mock_coll = vm
        doc_id = await instance.add_preference("language", "Chinese")
        assert doc_id == "pref_language"
        mock_coll.delete.assert_called_once_with(ids=["pref_language"])
        mock_coll.add.assert_called_once()
        _args, kwargs = mock_coll.add.call_args
        assert kwargs["documents"] == ["language: Chinese"]
        assert kwargs["metadatas"][0]["key"] == "language"
        assert kwargs["metadatas"][0]["value"] == "Chinese"

    @pytest.mark.asyncio
    async def test_add_preference_delete_error(self, vm):
        instance, _client, mock_coll = vm
        mock_coll.delete.side_effect = ValueError("delete fail")
        doc_id = await instance.add_preference("k", "v")
        assert doc_id == "pref_k"
        mock_coll.add.assert_called_once()


# ─── search ────────────────────────────────────────────────────────


class TestSearch:
    @pytest.mark.asyncio
    async def test_search_all(self, vm):
        instance, _client, mock_coll = vm
        mock_coll.query.return_value = {
            "documents": [["result text"]],
            "metadatas": [[{"session_id": "s1"}]],
            "distances": [[0.42]],
        }
        results = await instance.search("test query", collection="all", n_results=5)
        # "all" queries 3 collections; each returns the same result when using the same mock
        assert len(results) == 3
        assert results[0]["text"] == "result text"
        assert results[0]["collection"] == "conversations"

    @pytest.mark.asyncio
    async def test_search_with_session_filter(self, vm):
        instance, _client, mock_coll = vm
        mock_coll.query.return_value = {
            "documents": [["session result"]],
            "metadatas": [[{"session_id": "abc"}]],
            "distances": [[0.1]],
        }
        results = await instance.search("q", collection="conversations", session_id="abc")
        assert len(results) == 1
        _call_args, call_kwargs = mock_coll.query.call_args
        assert call_kwargs.get("where") == {"session_id": "abc"}

    @pytest.mark.asyncio
    async def test_search_empty_results(self, vm):
        instance, _client, mock_coll = vm
        mock_coll.query.return_value = {
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }
        results = await instance.search("nothing", collection="all")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_knowledge_collection(self, vm):
        instance, _client, _mock_coll = vm
        results = await instance.search("q", collection="knowledge")
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_invalid_collection(self, vm):
        instance, _client, _mock_coll = vm
        results = await instance.search("q", collection="nonexistent")
        assert results == []


# ─── get_stats / delete_session ────────────────────────────────────


class TestStatsAndDelete:
    @pytest.mark.asyncio
    async def test_get_stats(self, vm):
        instance, _client, mock_coll = vm
        mock_coll.count.return_value = 3
        stats = await instance.get_stats()
        assert stats["conversations"] == 3
        assert stats["knowledge"] == 3
        assert stats["preferences"] == 3

    @pytest.mark.asyncio
    async def test_delete_session(self, vm):
        instance, _client, mock_coll = vm
        mock_coll.get.return_value = {"ids": ["id1", "id2"]}
        await instance.delete_session("sess-1")
        mock_coll.get.assert_called_once_with(where={"session_id": "sess-1"})
        mock_coll.delete.assert_called_once_with(ids=["id1", "id2"])

    @pytest.mark.asyncio
    async def test_delete_session_no_ids(self, vm):
        instance, _client, mock_coll = vm
        mock_coll.get.return_value = {"ids": []}
        await instance.delete_session("empty-sess")
        mock_coll.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_session_error(self, vm):
        instance, _client, mock_coll = vm
        mock_coll.get.side_effect = ValueError("get fail")
        # should not raise
        await instance.delete_session("bad")
