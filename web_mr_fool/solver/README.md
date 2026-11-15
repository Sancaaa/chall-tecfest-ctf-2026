# Solver: Mr. Fool

Reference exploit solver for Mr. Fool (TecFest CTF 2026).

## Requirements

The solver requires Python 3 and the standard `requests` library. No C-extensions or third-party crypto tools are required.

```bash
pip install requests
```

## Usage

Run the solver against a local container or a remote instance:

```bash
# Default target (http://localhost:13400)
python solve.py

# Custom target positional
python solve.py http://localhost:13400

# Custom target flag style
python solve.py --url http://target-host:13400
```

## Exploitation Sequence

1. **S9: Seer**: Inspect `/s9/seer/robots.txt` and `/s9/seer/hidden` to obtain token `seer_sees_all`.
2. **S8: Clown**: Submit SQLi payload `x' UNION SELECT id, secret_code, name FROM potion_secrets--` to `/s8/clown/joke` to leak token `laughing_error_s8`.
3. **S7: Magician**: Send JSON payload `{"name": "Fireball", "type": "evocation", "approved": true}` to `/s7/magician/api/spells/create` to obtain token `unauthorized_spell`.
4. **S6: Faceless**: Forge base64 token with `username: "admin"` and `role: "admin"` to access `/s6/faceless/admin` and obtain token `forged_identity`.
5. **S3: Scholar of Yore**: Traverse to `../secrets/lfi_token.txt` via `/s3/scholar/view` to obtain token `scholar_reading_deep`.
6. **S0: The Fool**: Access `/s0/fool` to retrieve the flag `TecFest26{h34rtb34t_h34rtbr34k_4ll_0v3r_g4l4u_p4r4h_b4ng3t}`.
