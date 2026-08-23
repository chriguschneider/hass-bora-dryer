Title: BORA dryer integration — bring your Roth-Kippe BORA onto your dashboard

Category: Share your Projects!

Posted 2026-08-08: <https://community.home-assistant.io/t/bora-dryer-integration-bring-your-roth-kippe-bora-onto-your-dashboard-and-a-petition-for-control/1020437>

Revised 2026-08-23: petition wording replaced by the vendor-dialogue status after
Roth-Kippe replied (see issue #3). The live forum post still needs to be edited by
hand to match this draft (title: drop "and a petition for control"; the two petition
blocks; the P.S.).

---

Hi everyone,

You know that moment when you walk down to the basement for the third time just to
check whether the dryer is *finally* done? The Roth-Kippe BORA has a WLAN interface
that could answer that from your phone — but out of the box it only lives on the
machine's own little web page. So I wrote a Home Assistant integration that pulls it
onto your dashboard.

![The BORA device page in Home Assistant while drying — sensors, controls, LCD mirror and activity log](https://raw.githubusercontent.com/chriguschneider/hass-bora-dryer/master/images/device-page.png)

> 🙋 **BORA owners:** Roth-Kippe is in dialogue with us about a local control
> API. If you'd use one, a 👍 on
> [issue #4](https://github.com/chriguschneider/hass-bora-dryer/issues/4) is how
> we show them the demand. Details below.

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

**Wrap your smart plug (Shelly & friends)**

If you already have a smart plug in front of the dryer — a Shelly PM, for
example — the integration's options let you attach it to the BORA device:

![The BORA options dialog — smart plug entities, fallback sensors and the filter reminder settings](https://raw.githubusercontent.com/chriguschneider/hass-bora-dryer/master/images/options-dialog.png)

- The plug's **switch** becomes a `Power` control on the BORA device — one place
  to cut and restore power.
- Its **power and energy sensors** are mirrored under the BORA device, so
  consumption history lives with the dryer instead of with the plug.
- **Temperature / humidity fallback sensors** keep the room climate readings
  alive while the BORA itself is powered down.
- The **filter maintenance reminder** (threshold and on/off) is configured here
  too.

**The honest catch**

The BORA's interface is **read-only**. You can't start/stop a program or reset the
filter counter over the network — the manufacturer built the WLAN side purely as a
status mirror. The only write it exposes is setting the clock. So for now, on/off is
done with a smart plug in front of the machine.

Which brings me to where control stands 👇

**Device control: the vendor dialogue**

I think a modern heat-pump dryer should be able to *start on solar surplus* and
*reset its own filter counter*. That needs Roth-Kippe to add a tiny local control
API. I asked them — and they answered: no API today and no concrete roadmap, but the
firmware is available to owners on request, and their engineers consider extended
functions "theoretically solvable without replacing hardware". The whole exchange
is documented openly in [issue #3](https://github.com/chriguschneider/hass-bora-dryer/issues/3).

If you own a BORA and would use a control API, a 👍 on
[issue #4](https://github.com/chriguschneider/hass-bora-dryer/issues/4) (optionally
with your model + firmware version) is what I pass on to Roth-Kippe as customer
feedback. A roadmap needs demand; this is how owners can show it.

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

**P.S.** If you own a BORA and want real start/stop control one day: a 👍 on
[issue #4](https://github.com/chriguschneider/hass-bora-dryer/issues/4) takes ten
seconds and goes straight into the conversation with Roth-Kippe.
