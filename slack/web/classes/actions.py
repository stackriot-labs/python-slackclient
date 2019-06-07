from abc import ABCMeta, abstractmethod
from typing import Iterable, Union

from .objects import (
    ButtonStyle,
    DynamicTypes,
    JsonObject,
    Option,
    OptionGroup,
    OptionType,
)
from ...errors import SlackObjectFormationError


class Action(JsonObject):
    """
    Base class for interactive attachment elements - buttons and dropdowns
    """

    attributes = {"name", "text", "type", "url"}

    def __init__(self, text: str, type: str, name: str = None, url: str = None):
        self.name = name
        self.url = url
        self.text = text
        self.type = type

    def get_json(self) -> dict:
        if self.name is None and self.url is None:
            # If URL is populated but not name, this is a LinkButton, so name is not
            # needed
            raise SlackObjectFormationError("Action must have a name")
        return self.get_non_null_keys(self.attributes)


class ActionConfirmation(JsonObject):
    """
    Protect users from destructive actions or particular distinguished decisions by
    asking them to confirm their button click one more time. Use confirmation dialogs
    with care.
    """

    attributes = {"title", "text", "ok_text", "dismiss_text"}

    def __init__(
        self,
        text: str,
        title: str = None,
        ok_text: str = "Okay",
        dismiss_text: str = "Cancel",
    ):
        self.text = text
        self.title = title
        self.ok_text = ok_text
        self.dismiss_text = dismiss_text

    def get_json(self) -> dict:
        return self.get_non_null_keys(self.attributes)


class Button(Action):
    def __init__(
        self,
        name: str,
        text: str,
        value: str,
        confirm: ActionConfirmation = None,
        style: Union[ButtonStyle, str] = None,
    ):
        """
        Simple button for use inside attachments
        :param name: name of the element, important for interactive buttons
        :param text: text to display on the button
        :param value: the internal value to send on interaction
        :param confirm: an ActionConfirmation object
        :param style: "primary" or "danger" to represent important buttons
        """
        super().__init__(name=name, text=text, type="button")
        self.value = value
        self.confirm = confirm
        self.style = self.get_raw_value(style)

    def get_json(self) -> dict:
        if self.style is not None and not ButtonStyle.contains(self.style):
            raise SlackObjectFormationError(
                "style attribute must be one of the following values: "
                f"{ButtonStyle.pretty_print()}"
            )
        json = super().get_json()
        json.update(self.get_non_null_keys({"value", "style"}))
        if self.confirm:
            json["confirm"] = self.confirm.get_json()
        return json


class LinkButton(Action):
    def __init__(self, text: str, url: str):
        """
        A simple interactive button that simply opens a URL
        :param text: text to display on the button, eg 'Click Me!"
        :param url: the URL to open
        """
        super().__init__(text=text, url=url, type="button")


class MessageDropdown(Action, metaclass=ABCMeta):
    attributes = {"name", "text", "value", "type"}

    @property
    @abstractmethod
    def property_key(self) -> str:
        pass

    @property
    @abstractmethod
    def data_source(self) -> str:
        pass

    def __init__(
        self,
        name: str,
        text: str,
        options: Iterable[Union[Option, OptionGroup]] = None,
        selected_option: Union[Option, OptionGroup] = None,
    ):
        super().__init__(text=text, name=name, type="select")
        if self.data_source != "static":
            self.options = list(options)
        else:
            self.options = None
        self.selected_option = selected_option

    def get_json(self) -> dict:
        json = self.get_non_null_keys(self.attributes)
        if self.data_source != "static":
            if not 0 < len(self.options) <= 100:
                raise SlackObjectFormationError("Invalid number of options")
            json[self.property_key] = [
                o.get_json(OptionType.DIALOG) for o in self.options
            ]
        json["data_source"] = self.data_source
        return json


class OptionsMessageDropdown(MessageDropdown):
    data_source = "static"
    property_key = "options"

    def __init__(self, name: str, text: str, options: Iterable[Option], **kwargs):
        super().__init__(name=name, text=text, options=options, **kwargs)


class OptionGroupMessageDropdown(MessageDropdown):
    data_source = "static"
    property_key = "options_group"

    def __init__(self, name: str, text: str, options: Iterable[OptionGroup], **kwargs):
        super().__init__(name=name, text=text, options=options, **kwargs)


class DynamicMessageDropdown(MessageDropdown):
    property_key = "options"

    def __init__(
        self, name: str, text: str, source: Union[DynamicTypes, str], **kwargs
    ):
        super().__init__(name=name, text=text, **kwargs)
        self._source = self.get_raw_value(source)

    @property
    def data_source(self) -> str:
        return self._source

    def get_json(self) -> dict:
        if not DynamicTypes.contains(self._source):
            raise SlackObjectFormationError(
                "source attribute must be one of the following values: "
                f"{DynamicTypes.pretty_print()}"
            )
        json = super().get_json()
        return json


class ExternalMessageDropdown(MessageDropdown):
    data_source = "external"
    property_key = "options"

    def __init__(
        self,
        name: str,
        label: str,
        selected_option: Option = None,
        min_query_length: int = None,
        **kwargs
    ):
        super().__init__(name, label, **kwargs)
        self.selected_option = selected_option
        self.min_query_length = min_query_length

    def get_json(self) -> dict:
        json = super().get_json()
        json.update(self.get_non_null_keys({"min_query_length"}))
        if self.selected_option is not None:
            json["selected_option"] = [
                self.selected_option.get_json(OptionType.INTERACTIVE_MESSAGE)
            ]
        return json
