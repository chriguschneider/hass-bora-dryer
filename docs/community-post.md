Title: BORA dryer integration — bring your Roth-Kippe BORA onto your dashboard (and a petition for control)

Category: Share your Projects!

---

Hi everyone,

You know that moment when you walk down to the basement for the third time just to
check whether the dryer is *finally* done? The Roth-Kippe BORA has a WLAN interface
that could answer that from your phone — but out of the box it only lives on the
machine's own little web page. So I wrote a Home Assistant integration that pulls it
onto your dashboard.

![The BORA device page in Home Assistant while drying — sensors, controls, LCD mirror and activity log](https://raw.githubusercontent.com/chriguschneider/hass-bora-dryer/master/images/device-page.png)

> 📣 **BORA owners:** there's a [petition asking Roth-Kippe for an open local
> control API](https://github.com/chriguschneider/hass-bora-dryer/issues/4) —
> one 👍 on the pinned issue is your signature. Details below.

**What it gives you**

It reads the BORA's local status server every 60 seconds and turns it into proper
Home Assistant entities, all grouped under one device:

- **`Drying` binary sensor** — drive a "laundry's done" notification, or gate an
  automation on it.
- **Filter wear** — operating hours, remaining hours, a usage %, and a maintenance
  reminder that fires **once** when the filter is due and clears itself when you reset
  it on the machine.
- **Room climate** — the BORA's own temperature and humidity, with optional fallback
  to an external sensor while the dryer is powered down.
- **LCD mirror** — a `Display` camera entity showing the machine's current screen.
- **Power & energy** — point it at the smart plug in front of the dryer and those
  readings show up under the same device.

Everything is **local**: no cloud, no account, no vendor server in the loop.

**The honest catch**

The BORA's interface is **read-only**. You can't start/stop a program or reset the
filter counter over the network — the manufacturer built the WLAN side purely as a
status mirror. The only write it exposes is setting the clock. So for now, on/off is
done with a smart plug in front of the machine.

Which brings me to a small ask 👇

**A petition for an open API**

I think a modern heat-pump dryer should be able to *start on solar surplus* and
*reset its own filter counter*. That needs Roth-Kippe to publish a tiny local control
API. So there's a petition: if you own a BORA, a 👍 on the pinned GitHub issue tells
them owners actually want this. The more names, the stronger the case.
→ https://github.com/chriguschneider/hass-bora-dryer/issues/4

**Install**

HACS → custom repository (category *Integration*):
`https://github.com/chriguschneider/hass-bora-dryer` → install → restart → add the
integration and enter your BORA's IP. Full entity list, options and a security note
are in the README.

Tested on a **BORA 410 (firmware V1.0.006)**; it should work across the whole 4xx
series (408/410/415/420) since they share a controller. Running a different model?
Drop the contents of `http://<bora-ip>/info.html` in an issue and I'll confirm it.

**⚠️ Security note:** the BORA web interface is unauthenticated — anyone on the same
network can read its status and even the WLAN password in plaintext. Put it on an
isolated IoT VLAN.

Feedback, bug reports and BORA screenshots very welcome — GitHub issues or right here
in the thread.

Repo: https://github.com/chriguschneider/hass-bora-dryer

**P.S.** If you take one thing from this post: **👍 the
[petition](https://github.com/chriguschneider/hass-bora-dryer/issues/4)** if you
own a BORA. It costs ten seconds and it's the only lever we have for real
start/stop control.
