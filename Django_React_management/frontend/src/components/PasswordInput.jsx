import "./PasswordInput.css";

export default function PasswordInput({
  value,
  onChange,
  name,
  id,
  placeholder = "",
  required,
  minLength,
  autoComplete,
  className = "",
}) {
  return (
    <div className={`password-input-wrap ${className}`}>
      <input
        type="password"
        name={name}
        id={id}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        required={required}
        minLength={minLength}
        autoComplete={autoComplete}
        className="password-input"
      />
    </div>
  );
}
