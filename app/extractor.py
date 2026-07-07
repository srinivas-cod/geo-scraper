"""Business detail extraction placeholders."""

from __future__ import annotations

import logging
import re
from typing import Any

from app.models import Business
from app.selectors import Selectors


class BusinessExtractor:
    """Extract structured business details from an opened business view."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        """Initialize the extractor with an optional logger."""

        self.logger = logger or logging.getLogger(__name__)

    def _get_detail_panel(self, context: Any) -> Any:
        """Return the Google Maps business detail panel locator."""

        return context.locator(Selectors.DETAIL_PANEL).first

    def _get_detail_header(self, context: Any) -> Any:
        """Return the header area of the Google Maps business detail panel."""

        detail_panel = self._get_detail_panel(context)
        return detail_panel.locator(Selectors.DETAIL_PANEL_HEADER).first

    def _safe_text(self, locator: Any) -> str | None:
        """Safely extract trimmed text content from a locator."""

        try:
            if locator.count() == 0:
                return None
            text = (locator.first.text_content() or "").strip()
        except Exception:
            return None
        return text or None

    def _safe_attribute(self, locator: Any, attribute_name: str) -> str | None:
        """Safely extract an attribute value from a locator."""

        try:
            if locator.count() == 0:
                return None
            value = locator.first.get_attribute(attribute_name)
        except Exception:
            return None
        return value.strip() if value else None

    def extract_name(self, context: Any) -> str | None:
        """Extract the business name from the current page context."""

        detail_panel = self._get_detail_panel(context)
        return self._safe_text(detail_panel.locator(Selectors.BUSINESS_NAME))

    def extract_category(self, context: Any) -> str | None:
        """Extract the business category from the current page context."""

        detail_header = self._get_detail_header(context)
        return self._safe_text(detail_header.locator(Selectors.CATEGORY))

    def extract_rating(self, context: Any) -> float | None:
        """Extract the rating value from the current page context."""

        detail_header = self._get_detail_header(context)
        rating_locator = detail_header.locator(Selectors.RATING)

        # Primary: aria-label on the rating span (e.g. "4.7 stars")
        rating_value = self._safe_attribute(rating_locator, "aria-label")
        # Secondary: text content of the rating span only (not the full header)
        if rating_value is None:
            rating_value = self._safe_text(rating_locator)
        if rating_value is None:
            return None

        match = re.search(r"(\d+(?:\.\d+)?)", rating_value)
        if not match:
            return None

        try:
            value = float(match.group(1))
            # Ratings must be in the valid Google Maps range
            return value if 1.0 <= value <= 5.0 else None
        except ValueError:
            return None

    def extract_reviews(self, context: Any) -> int | None:
        """Extract the review count from the current page context."""

        detail_panel = self._get_detail_panel(context)
        detail_header = self._get_detail_header(context)

        # Strategy 1: Cascade through review button selectors (jsaction → aria → legacy)
        for selector in (Selectors.REVIEWS, Selectors.REVIEWS_ARIA, Selectors.REVIEWS_LEGACY):
            review_locator = detail_panel.locator(selector)
            review_text = self._safe_attribute(review_locator, "aria-label")
            if not review_text:
                review_text = self._safe_text(review_locator)
            if review_text:
                result = self._parse_review_count(review_text)
                if result is not None:
                    return result

        # Strategy 2: Parse from the rating span aria-label which sometimes contains
        # both rating and review count together, e.g. "4.5 stars, 1,200 reviews"
        rating_text = self._safe_attribute(
            detail_header.locator(Selectors.RATING), "aria-label"
        )
        if rating_text:
            result = self._parse_review_count(rating_text)
            if result is not None:
                return result

        return None

    def _parse_review_count(self, text: str) -> int | None:
        """Parse a review count integer from a text string."""

        # Handle K/k suffix (e.g. "1.2K reviews" -> 1200)
        k_match = re.search(r"([\d]+(?:\.[\d]+)?)\s*[Kk]\b", text)
        if k_match:
            try:
                return int(float(k_match.group(1)) * 1000)
            except ValueError:
                pass

        # Standard comma-separated number (e.g. "1,234 reviews" or "(1,234)")
        std_match = re.search(r"(\d[\d,]*)", text)
        if std_match:
            try:
                return int(std_match.group(1).replace(",", ""))
            except ValueError:
                pass

        return None

    def extract_address(self, context: Any) -> str | None:
        """Extract the street address from the current page context."""

        detail_panel = self._get_detail_panel(context)
        address_value = self._safe_attribute(detail_panel.locator(Selectors.ADDRESS), "aria-label")
        if address_value and address_value.lower().startswith("address:"):
            return address_value.split(":", 1)[1].strip()
        return self._safe_text(detail_panel.locator(Selectors.ADDRESS))

    def extract_phone(self, context: Any) -> str | None:
        """Extract the business phone number from the current page context."""

        detail_panel = self._get_detail_panel(context)
        phone_value = self._safe_attribute(detail_panel.locator(Selectors.PHONE), "aria-label")
        if phone_value and phone_value.lower().startswith("phone:"):
            return phone_value.split(":", 1)[1].strip()
        return self._safe_text(detail_panel.locator(Selectors.PHONE))

    def extract_website(self, context: Any) -> str | None:
        """Extract the business website URL from the current page context."""

        detail_panel = self._get_detail_panel(context)
        return self._safe_attribute(detail_panel.locator(Selectors.WEBSITE), "href")

    def extract_hours(self, context: Any) -> str | None:
        """Extract the business operating hours from the current page context."""

        detail_panel = self._get_detail_panel(context)
        hours_value = self._safe_attribute(detail_panel.locator(Selectors.HOURS), "aria-label")
        if not hours_value:
            return None
        return hours_value.replace(", Copy open hours", "").strip()

    def extract_coordinates(self, context: Any) -> tuple[float | None, float | None]:
        """Extract latitude and longitude from the current page context."""

        google_maps_url = self.extract_google_url(context)
        if not google_maps_url:
            return None, None

        match = re.search(r"!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)", google_maps_url)
        if match:
            return float(match.group(1)), float(match.group(2))

        fallback_match = re.search(r"@(-?\d+\.\d+),(-?\d+\.\d+)", google_maps_url)
        if fallback_match:
            return float(fallback_match.group(1)), float(fallback_match.group(2))

        return None, None

    def extract_google_url(self, context: Any) -> str | None:
        """Extract the canonical Google Maps URL from the current page context."""

        try:
            return context.url
        except Exception:
            return None

    def extract(self, context: Any) -> dict[str, str | float | int | None]:
        """Extract all supported business fields into a structured dictionary.

        Uses a single atomic JavaScript evaluation to find the correct
        visible detail panel and extract all fields at once. This avoids
        race conditions where separate Playwright locator calls resolve
        to different (cached/stale) DOM panels.
        """

        try:
            data = context.evaluate("""
                () => {
                    // Find the correct visible detail panel
                    const panels = document.querySelectorAll('div[role="main"][aria-label]');
                    let activePanel = null;
                    for (const panel of panels) {
                        // Skip the results feed panel
                        if (panel.querySelector('[role="feed"]')) continue;
                        const rect = panel.getBoundingClientRect();
                        const isOnScreen = rect.width > 0 && rect.height > 0
                            && rect.left >= -50 && rect.left < window.innerWidth;
                        const h1 = panel.querySelector('h1');
                        if (isOnScreen && h1 && h1.textContent.trim()) {
                            activePanel = panel;
                        }
                    }
                    if (!activePanel) return null;

                    // Helper to safely get text
                    const safeText = (el) => el ? (el.textContent || '').trim() || null : null;
                    const safeAttr = (el, attr) => el ? (el.getAttribute(attr) || '').trim() || null : null;

                    // Extract business name
                    const nameEl = activePanel.querySelector('h1.DUwDvf, h1');
                    const businessName = safeText(nameEl);

                    // Extract category
                    const headerDiv = activePanel.querySelector('div.lMbq3e');
                    const catEl = headerDiv ? headerDiv.querySelector('button.DkEaL') : null;
                    const category = safeText(catEl);

                    // Extract rating
                    let rating = null;
                    const ratingEl = headerDiv ? headerDiv.querySelector('span.ZkP5Je[role="img"]') : null;
                    if (ratingEl) {
                        const ratingLabel = ratingEl.getAttribute('aria-label') || ratingEl.textContent || '';
                        const ratingMatch = ratingLabel.match(/(\\d+(?:\\.\\d+)?)/);
                        if (ratingMatch) {
                            const val = parseFloat(ratingMatch[1]);
                            if (val >= 1.0 && val <= 5.0) rating = val;
                        }
                    }

                    // Extract review count
                    let reviewCount = null;
                    const reviewSelectors = [
                        'button[jsaction*="pane.rating.moreReviews"]',
                        '[aria-label*="review" i][role="button"]',
                        'button[aria-label*="review" i]:not([aria-label*="Write" i])'
                    ];
                    for (const sel of reviewSelectors) {
                        const el = activePanel.querySelector(sel);
                        if (el) {
                            const txt = el.getAttribute('aria-label') || el.textContent || '';
                            const kMatch = txt.match(/(\\d+(?:\\.\\d+)?)\\s*[Kk]\\b/);
                            if (kMatch) { reviewCount = Math.round(parseFloat(kMatch[1]) * 1000); break; }
                            const nMatch = txt.match(/(\\d[\\d,]*)/);
                            if (nMatch) { reviewCount = parseInt(nMatch[1].replace(/,/g, '')); break; }
                        }
                    }

                    // Extract address
                    let address = null;
                    const addrEl = activePanel.querySelector('[data-item-id="address"]');
                    if (addrEl) {
                        const addrLabel = addrEl.getAttribute('aria-label') || '';
                        if (addrLabel.toLowerCase().startsWith('address:')) {
                            address = addrLabel.split(':').slice(1).join(':').trim();
                        } else {
                            address = safeText(addrEl);
                        }
                    }

                    // Extract phone
                    let phone = null;
                    const phoneEl = activePanel.querySelector('button[data-item-id^="phone:tel:"]');
                    if (phoneEl) {
                        const phoneLabel = phoneEl.getAttribute('aria-label') || '';
                        if (phoneLabel.toLowerCase().startsWith('phone:')) {
                            phone = phoneLabel.split(':').slice(1).join(':').trim();
                        } else {
                            phone = safeText(phoneEl);
                        }
                    }

                    // Extract website
                    const websiteEl = activePanel.querySelector('a[data-item-id="authority"]');
                    const website = websiteEl ? websiteEl.getAttribute('href') || null : null;

                    // Extract hours
                    let hours = null;
                    const hoursEl = activePanel.querySelector('button[aria-label*="Copy open hours"]');
                    if (hoursEl) {
                        hours = (hoursEl.getAttribute('aria-label') || '').replace(', Copy open hours', '').trim() || null;
                    }

                    // Get current URL for coordinates
                    const pageUrl = window.location.href;
                    let latitude = null, longitude = null;
                    const coordMatch = pageUrl.match(/!3d(-?\\d+\\.\\d+)!4d(-?\\d+\\.\\d+)/);
                    if (coordMatch) {
                        latitude = parseFloat(coordMatch[1]);
                        longitude = parseFloat(coordMatch[2]);
                    } else {
                        const fallback = pageUrl.match(/@(-?\\d+\\.\\d+),(-?\\d+\\.\\d+)/);
                        if (fallback) {
                            latitude = parseFloat(fallback[1]);
                            longitude = parseFloat(fallback[2]);
                        }
                    }

                    return {
                        business_name: businessName,
                        category: category,
                        address: address,
                        phone: phone,
                        website: website,
                        rating: rating,
                        review_count: reviewCount,
                        opening_hours: hours,
                        google_maps_url: pageUrl,
                        latitude: latitude,
                        longitude: longitude
                    };
                }
            """)
        except Exception:
            self.logger.exception("Atomic JS extraction failed, falling back to locator-based extraction.")
            data = None

        if data is not None:
            return data

        # Fallback to original locator-based extraction
        latitude, longitude = self.extract_coordinates(context)
        return {
            "business_name": self.extract_name(context),
            "category": self.extract_category(context),
            "address": self.extract_address(context),
            "phone": self.extract_phone(context),
            "website": self.extract_website(context),
            "rating": self.extract_rating(context),
            "review_count": self.extract_reviews(context),
            "opening_hours": self.extract_hours(context),
            "google_maps_url": self.extract_google_url(context),
            "latitude": latitude,
            "longitude": longitude,
        }

    def extract_all(self, context: Any) -> Business:
        """Extract all supported business fields into a Business dataclass."""

        payload = self.extract(context)
        return Business(
            name=payload["business_name"],
            category=payload["category"],
            rating=payload["rating"],
            reviews=payload["review_count"],
            address=payload["address"],
            phone=payload["phone"],
            website=payload["website"],
            hours=payload["opening_hours"],
            google_maps_url=payload["google_maps_url"],
            latitude=payload["latitude"],
            longitude=payload["longitude"],
        )
