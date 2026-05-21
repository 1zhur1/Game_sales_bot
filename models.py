from dataclasses import dataclass


@dataclass
class GameDeal:
    title: str
    original_price: str
    discounted_price: str
    discount_percent: int
    rating_percent: int
    rating_text: str
    description: str
    url: str
    image: str
    store: str
    is_free: bool = False