from ..utils import DictView, ListView
from .utils import NEEDS_INITIALIZATION
from ..trees.utils import UNCHANGED


class BaseClient:
    def __init__(
        self,
        client,
        *,
        item,
        path,
        metadata,
        params,
    ):
        self._client = client
        if isinstance(path, str):
            raise ValueError("path is expected to be a list of segments")
        # Stash *immutable* copies just to be safe.
        self._path = tuple(path or [])
        if item is NEEDS_INITIALIZATION:
            self._item = None
            self._metadata = {}
        else:
            self._item = item
            self._metadata = metadata
        self._cached_len = None  # a cache just for __len__
        self._params = params or {}
        super().__init__()

    def __repr__(self):
        return f"<{type(self).__name__}>"

    @property
    def item(self):
        "JSON payload describing this item. Mostly for internal use."
        return self._item

    @property
    def metadata(self):
        "Metadata about this data source."
        # Ensure this is immutable (at the top level) to help the user avoid
        # getting the wrong impression that editing this would update anything
        # persistent.
        return DictView(self._metadata)

    @property
    def path(self):
        "Sequence of entry names from the root Tree to this entry"
        return ListView(self._path)

    @property
    def uri(self):
        "Direct link to this entry"
        return self.item["links"]["self"]

    @property
    def username(self):
        return self._client.username

    @property
    def offline(self):
        return self._client.offline

    @offline.setter
    def offline(self, value):
        self._client.offline = bool(value)

    def new_variation(
        self,
        metadata=UNCHANGED,
        path=UNCHANGED,
        params=UNCHANGED,
        **kwargs,
    ):
        """
        This is intended primarily for internal use and use by subclasses.
        """
        if metadata is UNCHANGED:
            metadata = self._metadata
        if path is UNCHANGED:
            path = self._path
        if params is UNCHANGED:
            params = self._params
        return type(self)(
            item=self._item,
            metadata=metadata,
            path=path,
            params=params,
            **kwargs,
        )


class BaseStructureClient(BaseClient):
    def __init__(
        self,
        client,
        *,
        structure=None,
        **kwargs,
    ):
        super().__init__(client, **kwargs)
        self._structure = structure

    def new_variation(self, structure=UNCHANGED, **kwargs):
        if structure is UNCHANGED:
            structure = self._structure
        return super().new_variation(structure=structure, **kwargs)

    def touch(self):
        """
        Access all the data.

        This causes it to be cached if the client is configured with a cache.
        """
        repr(self)
        self.read()

    def structure(self):
        """
        Return a dataclass describing the structure of the data.
        """
        # This is implemented by subclasses.
        pass


class BaseArrayClient(BaseStructureClient):
    """
    Shared by Array, DataArray, Dataset

    Subclass must define:

    * STRUCTURE_TYPE : type
    """

    def structure(self):
        # Notice that we are NOT *caching* in self._structure here. We are
        # allowing that the creator of this instance might have already known
        # our structure (as part of the some larger structure) and passed it
        # in.
        if self._structure is None:
            content = self._client.get_json(
                f"/metadata/{'/'.join(self._path)}",
                params={
                    "fields": ["structure.micro", "structure.macro"],
                    **self._params,
                },
            )
            result = content["data"]["attributes"]["structure"]
            structure = self.STRUCTURE_TYPE.from_json(result)
        else:
            structure = self._structure
        return structure
