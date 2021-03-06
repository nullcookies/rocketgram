# Copyright (C) 2015-2019 by Vd.
# This file is part of RocketGram, the modern Telegram bot framework.
# RocketGram is released under the MIT License (see LICENSE).


from itertools import accumulate, chain, cycle, repeat

from . import exceptions

MIN_BUTTONS = 1
MAX_BUTTONS = 8


class Keyboard:
    def __init__(self):
        self._buttons = list()
        self._options = dict()
        self._keyboard_type = None

    def row(self):
        if len(self._buttons) and self._buttons[-1]:
            self._buttons.append(None)
        return self

    def __assing_buttons(self, keyboard):
        btns = chain.from_iterable([p + q for p, q in zip(keyboard, repeat([None]))])
        self._buttons = list(btns)[:-1]

    def __check_scheme_values(self, *args):
        for l in args:
            for i in l:
                if i < MIN_BUTTONS or i > MAX_BUTTONS:
                    return False
        return True

    def __check_scheme_types(self, *args):
        for i in args:
            if type(i) not in (list, tuple):
                return False
        return True

    def arrange_scheme(self, head=None, middle=None, tail=None):
        if not head:
            head = []
        if not middle:
            middle = [1]
        if not tail:
            tail = []

        if not self.__check_scheme_types(head, middle, tail):
            raise TypeError('Scheme values must be list or tuple')

        if not self.__check_scheme_values(head, middle, tail):
            raise exceptions.KeyboardTooManyButtonsError('Too many buttons in a row. Must be from 1 to 8')

        btns = [b for b in self._buttons if b]

        if sum(head) + sum(tail) > len(btns):
            raise exceptions.NotEnoughButtonsError('Not egnought buttons to render scheme')

        head_btns = btns[:sum(head)]
        middle_btns = btns[sum(head):-sum(tail) if sum(tail) > 0 else None]
        tail_btns = btns[-sum(tail):]

        head_part = [head_btns[p:q] for p, q in zip(accumulate(chain([0], head)), accumulate(head))]

        middle_part = list()
        m = zip(accumulate(chain([0], cycle(middle))), accumulate(cycle(middle)))
        while True:
            p, q = next(m)
            part = middle_btns[p:q]
            if len(part):
                middle_part.append(part)
            else:
                break

        tail_part = [tail_btns[p:q] for p, q in zip(accumulate(chain([0], tail)), accumulate(tail))]

        self.__assing_buttons(chain(head_part + middle_part + tail_part))

        return self

    def arrange_simple(self, row=8):
        if row < MIN_BUTTONS or row > MAX_BUTTONS:
            raise exceptions.KeyboardTooManyButtonsError('Too many buttons in a row')

        btns = [b for b in self._buttons if b]
        l = len(btns) if len(btns) < row else row
        keyboard = [btns[i:i + row] for i in range(0, len(btns), row)]

        self.__assing_buttons(keyboard)

        return self

    def render(self):
        keyboard = list(list())
        cnt = 0
        for b in self._buttons:
            if b:
                if len(keyboard) < cnt + 1:
                    keyboard.append(list())
                keyboard[cnt].append(b)

                if len(keyboard[cnt]) > MAX_BUTTONS:
                    raise exceptions.KeyboardTooManyButtonsError('Too many buttons in a row')
            else:
                cnt += 1

        keyboard = {self._keyboard_type: keyboard}
        keyboard.update(self._options)
        return keyboard
