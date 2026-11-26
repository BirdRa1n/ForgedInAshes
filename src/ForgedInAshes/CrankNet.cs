// E01 Crank in multiplayer (F2-T06 for the crank): turning it is done by a client, but its generator (PowerItem)
// lives on the server.
//  - NetPackageFeCrankTurn (client -> server, every ~0.2 s while E is held): "I turned the crank at pos for N s".
//    The server checks it is a crank and the sender stands near it, then CrankServer.Apply adds the fuel, turns
//    the generator on and charges the battery with the overflow (same code path as the host / single player).
//  - NetPackageFeCrankSpin (server -> clients near the crank): every client spins that crank's rotor, so
//    everyone sees it turning, not only the player cranking.
// Stamina stays on the cranking player's side (like vanilla actions).
//
// Vanilla (IL 3.4.0 b10): NetPackageManager finds NetPackage subclasses with ReflectionHelpers.
// FindTypesImplementingBase, which includes ModManager.GetLoadedAssemblies (types need [Preserve]); package ids
// are synced to clients by name. NetPackage.write writes the package id first (call base.write).
// ConnectionManager.SendToServer / SendPackage(..., range around a world position).
//
// C# 5 only.

using System.Collections.Generic;
using UnityEngine;

namespace ForgedInAshes
{
    public static class CrankServer
    {
        const float MaxSecondsPerPackage = 0.5f;   // a client cannot claim more than this per package
        const int SpinBroadcastRange = 80;          // blocks

        static readonly Dictionary<Vector3i, float> pendingFuel = new Dictionary<Vector3i, float>();

        // Server side (host, single player, or dedicated server): seconds of cranking at pos become fuel.
        public static void Apply(World world, Vector3i pos, float seconds)
        {
            if (world == null) return;
            BlockFeCrank crank = world.GetBlock(pos).Block as BlockFeCrank;
            if (crank == null) return;
            seconds = Mathf.Clamp(seconds, 0f, MaxSecondsPerPackage);
            TileEntityPowerSource te = world.GetTileEntity(pos) as TileEntityPowerSource;
            PowerGenerator gen = PowerManager.HasInstance
                ? PowerManager.Instance.GetPowerItemByWorldPos(pos) as PowerGenerator : null;
            if (te == null || gen == null) return;

            float pf;
            pendingFuel.TryGetValue(pos, out pf);
            pf += crank.FuelPerSecond * seconds;
            int add = Mathf.FloorToInt(pf);
            pendingFuel[pos] = pf - add;
            if (add > 0)
            {
                int fuel = Mathf.Min(gen.MaxFuel, gen.CurrentFuel + add);
                int overflow = gen.CurrentFuel + add - fuel;
                gen.CurrentFuel = (ushort)fuel;
                if (!gen.IsOn) gen.IsOn = true;   // vanilla auto-turns it off when the fuel runs out
                // With the Battery Bank Module, what does not fit in the generator charges the battery
                // (1 fuel = 1 charge unit; CrankSlots.cs feeds it back when the fuel runs out).
                ItemStack battery = CrankSlots.ActiveBattery(gen.Stacks);
                int room = CrankSlots.Room(battery);
                if (overflow > 0 && room > 0) battery.itemValue.UseTimes -= Mathf.Min(overflow, room);
                te.SetModified();
            }
            BroadcastSpin(pos);
        }

        static void BroadcastSpin(Vector3i pos)
        {
            ConnectionManager cm = SingletonMonoBehaviour<ConnectionManager>.Instance;
            if (cm == null || !cm.IsServer) return;
            NetPackageFeCrankSpin pkg = NetPackageManager.GetPackage<NetPackageFeCrankSpin>().Setup(pos);
            cm.SendPackage(pkg, false, -1, -1, -1, (Vector3?)pos.ToVector3(), SpinBroadcastRange, false);
        }
    }

    // Client side: send what the local player cranked (or apply it directly when this game is the server).
    public static class CrankNet
    {
        public static void Turn(Vector3i pos, float seconds)
        {
            ConnectionManager cm = SingletonMonoBehaviour<ConnectionManager>.Instance;
            if (cm == null) return;
            if (cm.IsServer)
            {
                CrankServer.Apply(GameManager.Instance.World, pos, seconds);
                return;
            }
            cm.SendToServer(NetPackageManager.GetPackage<NetPackageFeCrankTurn>().Setup(pos, seconds), false);
        }
    }

    [UnityEngine.Scripting.Preserve]
    public class NetPackageFeCrankTurn : NetPackage
    {
        const float MaxDistanceSq = 6f * 6f;   // the sender must be near the crank

        Vector3i pos;
        float seconds;

        public NetPackageFeCrankTurn Setup(Vector3i _pos, float _seconds)
        {
            pos = _pos;
            seconds = _seconds;
            return this;
        }

        public override NetPackageDirection PackageDirection
        {
            get { return NetPackageDirection.ToServer; }
        }

        public override void read(PooledBinaryReader _reader)
        {
            pos = new Vector3i(_reader.ReadInt32(), _reader.ReadInt32(), _reader.ReadInt32());
            seconds = _reader.ReadSingle();
        }

        public override void write(PooledBinaryWriter _writer)
        {
            base.write(_writer);
            _writer.Write(pos.x);
            _writer.Write(pos.y);
            _writer.Write(pos.z);
            _writer.Write(seconds);
        }

        public override void ProcessPackage(World _world, GameManager _callbacks)
        {
            if (_world == null) return;
            ClientInfo sender = Sender;
            if (sender != null)
            {
                Entity e = _world.GetEntity(sender.entityId);
                if (e == null || (e.position - pos.ToVector3Center()).sqrMagnitude > MaxDistanceSq) return;
            }
            CrankServer.Apply(_world, pos, seconds);
        }
    }

    [UnityEngine.Scripting.Preserve]
    public class NetPackageFeCrankSpin : NetPackage
    {
        Vector3i pos;

        public NetPackageFeCrankSpin Setup(Vector3i _pos)
        {
            pos = _pos;
            return this;
        }

        public override NetPackageDirection PackageDirection
        {
            get { return NetPackageDirection.ToClient; }
        }

        public override void read(PooledBinaryReader _reader)
        {
            pos = new Vector3i(_reader.ReadInt32(), _reader.ReadInt32(), _reader.ReadInt32());
        }

        public override void write(PooledBinaryWriter _writer)
        {
            base.write(_writer);
            _writer.Write(pos.x);
            _writer.Write(pos.y);
            _writer.Write(pos.z);
        }

        public override void ProcessPackage(World _world, GameManager _callbacks)
        {
            if (_world == null) return;
            BlockFeCrank crank = _world.GetBlock(pos).Block as BlockFeCrank;
            CrankSpinner spinner = CrankSpinner.At(pos);
            if (crank != null && spinner != null) spinner.Drive(crank.SpinDegPerSecond, 0.35f);
        }
    }
}
